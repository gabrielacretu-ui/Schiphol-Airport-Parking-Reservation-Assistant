import json
from datetime import datetime
from typing import TypedDict, List

from langchain_classic.memory import ConversationBufferMemory
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langgraph.graph import START, END, StateGraph
from openai import OpenAI

from app.AGENT_ADMIN import agent_admin
from app.AGENT_CHATBOT import agent_chatbot
from app.GUARD_RAILS import sanitize_input_nl
from app.MCP_SERVER_calling import save_reservation_to_mcp_server
from INITIALIZATION_sqlite_db import get_sqlite_connection
from functions.FUNCTION_helpers_READ_tools import auto_release_expired_reservations
from tools.TOOLS_human_agent import check_advance_booking_tool, check_car_reservation_history_tool, check_reservation_length_tool
from tools.TOOLS_sqlite_READ import check_availability_tool, check_existing_reservation_tool, \
    get_parking_locations_tool, get_parking_information_tool
from tools.TOOLS_sqlite_WRITE import validate_reservation_tool, validate_cancellation_tool


class ParkingState(TypedDict, total=False):
    """
       TypedDict representing the state of a parking reservation conversation.

       Attributes:
           messages (List[BaseMessage]): List of messages exchanged in the conversation.
           data (dict): Any validated data from the chatbot, e.g., reservation details.
       """
    messages: List[BaseMessage]
    data: dict


# ---------------------------------------------------
# LLM & Agents
# ---------------------------------------------------

shared_memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)
chatbot_tools=[check_availability_tool, check_existing_reservation_tool,get_parking_locations_tool,validate_reservation_tool,get_parking_information_tool, validate_cancellation_tool]
admin_tools=[check_reservation_length_tool, check_car_reservation_history_tool, check_advance_booking_tool]
chatbot_executor = agent_chatbot(chatbot_tools, shared_memory)
admin_executor = agent_admin(admin_tools, shared_memory)


def agent_chatbot_calling(state: ParkingState):
    """
        Chatbot agent node.

        Args:
            state (ParkingState): Current conversation state.

        Returns:
            dict: Updated state with AIMessage appended and any validated data.
        """
    print("agent_chatbot_calling")
    user_input = state["messages"][-1].content
    output = chatbot_executor.invoke({"input": user_input})

    validated_dict = None

    for action, tool_output in reversed(output["intermediate_steps"]):
        if action.tool.startswith("validate_") and action.tool.endswith("_tool"):
            validated_dict = tool_output
            break

    ai_message = AIMessage(content=output["output"])
    print(ai_message)

    return {
        "messages": state["messages"] + [ai_message],
        "data": validated_dict
    }

def should_ask_admin_to_execute(state: ParkingState):
    """
        Decide if admin review is needed.

        Args:
            state (ParkingState): Current conversation state.

        Returns:
            str: Next node name or END.
        """
    print("should_ask_admin_to_execute")
    data = state.get("data")
    if not data:
        return END

    if data.get("operation") in ["making","cancelling","modifying"] and data.get("status") == "success":
        return "admin_chatbot_calling"

    return END

def admin_chatbot_calling(state: ParkingState):
    """
    Admin agent node.

    Args:
        state (ParkingState): Current conversation state.

    Returns:
        dict: Updated state with admin AIMessage appended.
    """
    print("admin_chatbot_calling")
    # Combine messages into a string for admin agent
    data=state["data"]
    print(data)

    ai_message = admin_executor.invoke({"input": json.dumps(data)})  # pass as dict with 'input'
    print(ai_message)

    # Wrap in AIMessage so ToolNode / graph can parse it
    admin_ai_message = AIMessage(content=ai_message["output"], tool_calls=getattr(ai_message, "tool_calls", []))


    return {"messages": state["messages"] + [admin_ai_message],"data":data}


def admin_condition_execution(state: ParkingState):
    """
        Determine if admin approved the operation.

        Args:
            state (ParkingState): Current conversation state.

        Returns:
            str: Next node ('mcp_logging') if approved, else END.
        """
    print("admin_condition_execution")

    last_message = state["messages"][-1].content.lower()
    print(f"This is the last message {last_message}")
    client=OpenAI()

    def is_approved(text):
        prompt = f"Does this message indicate approval? Answer 'yes' or 'no'.\nMessage: {text}"
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        # Correct attribute access
        answer = response.choices[0].message.content.strip().lower()
        return "yes" in answer
    if is_approved(last_message):
        return "mcp_logging"

    return END


def save_reservation_event_to_mcp_server(state: ParkingState):
    """
        Save approved reservation to MCP server, log and database for fast retrieval.

        Args:
            state (ParkingState): Current conversation state.

        Returns:
            dict: Updated state with AIMessage confirming logging.
        """
    entry = state["data"]
    save_reservation_to_mcp_server(entry)

    mcp_server_message = (
        "The reservation event request sent by the user, approved by the admin, "
        "has been successfully logged to our secure API endpoint and saved in our data file. As well as"
        "it was recorded in our database for fast retrieval"
    )
    ai_msg = AIMessage(content=mcp_server_message)
    return {"messages": state["messages"] + [ai_msg], "data": entry}



# ---------------------------------------------------
# Build the LangGraph
# ---------------------------------------------------

builder = StateGraph(ParkingState)

builder.add_node("agent_chatbot_calling",agent_chatbot_calling)
builder.add_node("admin_chatbot_calling",admin_chatbot_calling)
builder.add_node("mcp_logging", save_reservation_event_to_mcp_server)


builder.add_edge(START, "agent_chatbot_calling")
builder.add_conditional_edges(   "agent_chatbot_calling",   should_ask_admin_to_execute,   ["admin_chatbot_calling", END])
builder.add_conditional_edges("admin_chatbot_calling",admin_condition_execution,["mcp_logging", END])
builder.add_edge("mcp_logging",END)

react_graph = builder.compile()

# Show
# Save the mermaid PNG to disk
png_bytes = react_graph.get_graph(xray=True).draw_mermaid_png()
with open("graph.png", "wb") as f:
    f.write(png_bytes)

print("Graph saved as graph.png")

# ---------------------------------------------------
# Simple Call Example
# ---------------------------------------------------

def simple_call():
    """
        Run a simple single-step test of the LangGraph pipeline.
        """
    # Create initial state
    state: ParkingState = {
        "messages": [HumanMessage(
            content="My name is Andrea. I want to book a parking slot at Schiphol P1 Short Parking from April 7 at 12:00 to April 8 at 14:00 for car 4ZHZ18")],
        # data will be filled by nodes
        "data": {}
    }
    # Execute the graph
    messages = react_graph.invoke(state)
    for m in messages["messages"]:
        role = m.__class__.__name__.replace("Message", "")
        print(f"{role}: {m.content}\n")


def run_interactive():
    """
       Run a continuous interactive session with the parking assistant.
       Handles:
           - User input with sanitization
           - Timestamp prepending
           - LangGraph pipeline invocation
           - Displaying latest AI messages
       """

    from langchain_core.messages import HumanMessage

    print("\n🚗 Schiphol Parking Assistant")
    print("Type 'exit', 'quit', or 'bye' to stop.\n")

    state: ParkingState = {
        "messages": [],
        "data": {}
    }

    while True:

        # Ask user for input
        user_input = input("\nYou: ").strip()
        user_input = sanitize_input_nl(user_input)

        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        # Step 1: get current date and time dynamically (to the minute)
        now_str = datetime.now().strftime("%d-%m-%Y %H:%M")  # e.g., 15-03-2026 17:23

        # Step 2: prepend current date/time info to user input
        input_with_datetime = f"Today is {now_str}. {user_input}"

        # Add user message
        state["messages"].append(HumanMessage(content=input_with_datetime))

        try:

            # Run the LangGraph pipeline
            state = react_graph.invoke(state)

            # Print only the latest AI message
            last_message = state["messages"][-1]

            print(f"\nAI: {last_message.content}\n")

        except Exception as e:

            print("\n⚠️ System error occurred.")
            print(e)
            break

if __name__=="__main__":
    conn = get_sqlite_connection()
    auto_release_expired_reservations(conn)
    run_interactive()