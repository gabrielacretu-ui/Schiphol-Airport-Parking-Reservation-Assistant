# ---------------------------------------------------
# Agent Tools
# ---------------------------------------------------
import json
from datetime import datetime

from langchain_classic.memory import ConversationBufferMemory

from app.AGENT_ADMIN import agent_admin
from app.AGENT_CHATBOT import agent_chatbot
from app.GUARD_RAILS import sanitize_input_nl
from functions.FUNCTION_helpers_READ_tools import auto_release_expired_reservations
from INITIALIZATION_sqlite_db import get_sqlite_connection
from app.MCP_SERVER_calling import save_reservation_to_mcp_server
from tools.TOOLS_human_agent import check_reservation_length_tool, check_car_reservation_history_tool, check_advance_booking_tool
from tools.TOOLS_sqlite_READ import check_availability_tool, check_existing_reservation_tool, \
    get_parking_locations_tool, get_parking_information_tool
from tools.TOOLS_sqlite_WRITE import validate_reservation_tool, validate_cancellation_tool


# ---------------------------------------------------
# LLM & Agents
# ---------------------------------------------------
chatbot_tools=[check_availability_tool, check_existing_reservation_tool,get_parking_locations_tool,validate_reservation_tool,get_parking_information_tool, validate_cancellation_tool]
admin_tools=[check_reservation_length_tool, check_car_reservation_history_tool, check_advance_booking_tool]

shared_memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)

chatbot_executor = agent_chatbot(chatbot_tools, shared_memory)
admin_executor = agent_admin(admin_tools, shared_memory)

def run_interactive():
    """
        Run an interactive terminal session with the parking reservation chatbot.

        Workflow:
        1. Prompt user for input continuously.
        2. Sanitize input to remove sensitive data.
        3. Prepend current date/time to input.
        4. Pass input to chatbot agent and detect if a validation tool was invoked.
        5. If validation exists, pass it to admin agent for review.
        6. Check if admin approves using GPT-4.1-mini.
        7. If approved, save the reservation to the MCP server.
        8. Display chatbot and admin responses at each step.
        """
    print("=== Parking Reservation Chatbot ===")
    print("Type 'exit' to quit.")

    conn = get_sqlite_connection()
    auto_release_expired_reservations(conn)

    while True:

        user_input = input("\nYou: ").strip()
        user_input = sanitize_input_nl(user_input)
        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        now_str = datetime.now().strftime("%d-%m-%Y %H:%M")
        input_with_datetime = f"Today is {now_str}. {user_input}"

        # -----------------------------
        # Step 1: Chatbot processing
        # -----------------------------
        try:

            output = chatbot_executor.invoke({"input": input_with_datetime})

            validated_dict = None

            for action, tool_output in reversed(output["intermediate_steps"]):

                if action.tool.startswith("validate_") and action.tool.endswith("_tool"):
                    validated_dict = tool_output
                    break

        except Exception as e:
            print(f"Chatbot error: {e}")
            continue

        # -----------------------------
        # Step 2: Check validation result
        # -----------------------------
        # If no validation tool was triggered, just print chatbot response
        if validated_dict is None:
            print(f"Chatbot: {output.get('output')}")
            continue


        print(f"Chatbot: {output.get('output')}")
        if (not validated_dict.get("operation")) or validated_dict.get("status") != "success":
            print(f"Chatbot:{output.get('output')}")
            continue

        # -----------------------------
        # Step 3: Admin review
        # -----------------------------
        try:

            admin_response = admin_executor.invoke({
                "input": json.dumps(validated_dict)
            })

            admin_result = admin_response.get("output", {})

        except Exception as e:
            print(f"Admin error: {e}")
            continue

        # -----------------------------
        # Step 4: Final decision
        # -----------------------------
        from openai import OpenAI

        client = OpenAI()

        def is_approved(text):
            prompt = f"Does this message indicate approval? Answer 'yes' or 'no'.\nMessage: {text}"
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            # Correct attribute access
            answer = response.choices[0].message.content.strip().lower()
            return "yes" in answer

        if not is_approved(admin_result):
            print(f"Admin:{admin_result}")
            continue
        save_reservation_to_mcp_server(validated_dict)
        print("The reservation operation has been saved in the MCP server as a new log entry and in the database for fast access.")





if __name__ == "__main__":


    conn=get_sqlite_connection()
    auto_release_expired_reservations(conn)
    run_interactive()
