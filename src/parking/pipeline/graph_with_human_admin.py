from typing import TypedDict, List

from langchain_classic.memory import ConversationBufferMemory
from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph import START, END, StateGraph

from ..agents import agent_chatbot
from ..mcp import route_and_execute_mcp_tool
from ..services import send_approval_email, wait_for_decision
from ..tools import (
    check_availability_tool, check_existing_reservation_tool,
    get_parking_locations_tool, get_parking_information_tool,
    validate_make_reservation_tool, validate_cancellation_tool,
    validate_modification_tool, search_parking_information_tool,
)


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
# Tool lists — stateless, defined once at module level
# ---------------------------------------------------

_CHATBOT_TOOLS = [
    check_availability_tool, check_existing_reservation_tool,
    get_parking_locations_tool, validate_make_reservation_tool,
    get_parking_information_tool, validate_cancellation_tool,
    validate_modification_tool,search_parking_information_tool
]


# ---------------------------------------------------
# Graph factory
# ---------------------------------------------------

def build_graph():
    """
    Build and compile the parking reservation LangGraph pipeline.

    Wires up the following workflow:

        user input
            └─> agent_chatbot_calling
                    ├─ (no validation needed) ──> END
                    └─ (reservation action validated)
                            └─> human_admin_approval  (email sent, polls for decision)
                                    ├─ (rejected / timeout) ──> END
                                    └─ (approved)
                                            └─> mcp_logging ──> END

    Returns:
        CompiledStateGraph: Ready-to-invoke LangGraph pipeline.
    """
    chatbot_memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    chatbot_executor = agent_chatbot(_CHATBOT_TOOLS, chatbot_memory)

    # ------------------------------------------------------------------
    # Node functions are closures: they capture the executors and client
    # created above, so no global state is needed.
    # ------------------------------------------------------------------

    def agent_chatbot_calling(state: ParkingState) -> dict:
        """Invoke the chatbot agent and extract any validated reservation data."""
        user_input = state["messages"][-1].content
        output = chatbot_executor.invoke({"input": user_input})

        validated_dict = None
        for action, tool_output in reversed(output["intermediate_steps"]):
            if action.tool.startswith("validate_") and action.tool.endswith("_tool"):
                validated_dict = tool_output
                break

        return {
            "messages": state["messages"] + [AIMessage(content=output["output"])],
            "data": validated_dict,
        }

    def should_ask_admin(state: ParkingState) -> str:
        """Route to human admin approval if a reservation action was successfully validated."""
        data = state.get("data")
        if not data:
            return END
        if data.get("operation") in ["making", "cancelling", "modifying"] and data.get("status") == "success":
            return "human_admin_approval"
        return END

    def human_admin_approval(state: ParkingState) -> dict:
        """Send an approval email to the human admin and wait for their decision."""
        data = state["data"]
        token = send_approval_email(data)
        decision = wait_for_decision(token)
        message = AIMessage(content=f"Admin decision: {decision}.")
        return {"messages": state["messages"] + [message], "data": {**data, "admin_decision": decision}}

    def admin_condition_execution(state: ParkingState) -> str:
        """Route based on the human admin's decision."""
        decision = state["data"].get("admin_decision", "")
        return "mcp_logging" if decision == "approved" else END

    def save_reservation_event_to_mcp_server(state: ParkingState) -> dict:
        """Persist the approved reservation to the MCP server and database."""
        entry = state["data"]
        route_and_execute_mcp_tool(entry)
        mcp_server_message = (
            "The reservation event request sent by the user, approved by the admin, "
            "has been successfully logged to our secure API endpoint and saved in our data file. "
            "It was also recorded in our database for fast retrieval."
        )
        return {"messages": state["messages"] + [AIMessage(content=mcp_server_message)], "data": entry}

    # ------------------------------------------------------------------
    # Wire up the graph
    # ------------------------------------------------------------------

    graph = StateGraph(ParkingState)
    graph.add_node("agent_chatbot_calling", agent_chatbot_calling)
    graph.add_node("human_admin_approval", human_admin_approval)
    graph.add_node("mcp_logging", save_reservation_event_to_mcp_server)

    graph.add_edge(START, "agent_chatbot_calling")
    graph.add_conditional_edges("agent_chatbot_calling", should_ask_admin, ["human_admin_approval", END])
    graph.add_conditional_edges("human_admin_approval", admin_condition_execution, ["mcp_logging", END])
    graph.add_edge("mcp_logging", END)

    return graph.compile()