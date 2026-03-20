# ---------------------------------------------------
# Agent Tools+memory
# ---------------------------------------------------
import json
from datetime import datetime

from langchain_classic.memory import ConversationBufferMemory

from app.AGENT_ADMIN import agent_admin
from app.AGENT_CHATBOT import agent_chatbot
from app.GUARD_RAILS import sanitize_input_nl
from functions.FUNCTION_helpers_READ_tools import auto_release_expired_reservations
from INITIALIZATION_sqlite_db import get_sqlite_connection
from tools.TOOLS_human_agent import check_reservation_length_tool, check_car_reservation_history_tool, check_advance_booking_tool
from tools.TOOLS_sqlite_READ import check_availability_tool, check_existing_reservation_tool, \
    get_parking_locations_tool, get_parking_information_tool
from tools.TOOLS_sqlite_WRITE import validate_reservation_tool, validate_cancellation_tool
from tools.TOOLS_weaviate import search_parking_information_tool

# ---------------------------------------------------
# LLM & Agents
# ---------------------------------------------------
chatbot_tools=[check_availability_tool, check_existing_reservation_tool,get_parking_locations_tool,validate_reservation_tool,get_parking_information_tool, validate_cancellation_tool, search_parking_information_tool]
admin_tools=[check_reservation_length_tool, check_car_reservation_history_tool, check_advance_booking_tool]

shared_memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)
chatbot_executor = agent_chatbot(chatbot_tools, shared_memory)
admin_executor = agent_admin(admin_tools, shared_memory)
# ---------------------------------------------------
# Interactive loop: Chatbot + Admin interaction
# ---------------------------------------------------

def run_interactive():
    """
       Launch an interactive terminal session with the parking reservation chatbot.

       Features:
       - Prompts the user continuously for input until 'exit' or 'quit' is typed.
       - Sanitizes user input to remove sensitive data.
       - Prepends current date/time to the user input for context.
       - Passes the input to the chatbot agent for processing.
       - Checks if a validation tool was invoked during processing.
       - If a reservation or cancellation is validated, sends it for admin review.
       - Prints chatbot responses and final admin decision.

       Steps:
       1. Get user input.
       2. Sanitize input and prepend timestamp.
       3. Invoke chatbot agent and check for validation tool outputs.
       4. If validation exists, invoke admin agent for review.
       5. Print final results.
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

        print(f"Admin:{admin_result}")

def run_automated_test(questions: list):
    """
        Run an automated batch test of the chatbot and admin agents.

        Args:
            questions (list[str]): List of user queries to test.

        Features:
        - Sanitizes input and prepends timestamp for each query.
        - Processes each query through the chatbot.
        - Checks for validation tool outputs.
        - Sends validated actions for admin review.
        - Prints both chatbot responses and admin decisions.
        - Continues to the next query on errors.

        Usage:
            run_automated_test(["Query 1", "Query 2", ...])
        """

    print("=== Automated Parking Reservation Chatbot Test ===")


    conn = get_sqlite_connection()
    auto_release_expired_reservations(conn)

    for user_input in questions:
        print(f"\nYou: {user_input}")

        user_input = sanitize_input_nl(user_input)

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

        print(f"Admin:{admin_result}")

    print("\n=== Automated Test Completed ===")
if __name__ == "__main__":

    conn = get_sqlite_connection()
    auto_release_expired_reservations(conn)
    run_interactive()

    tests=[
    "I want to book a parking spot at Schiphol P1 Short Parking from 1 April 2026 09:00 to 1 April 2026 12:00. My name is Jan de Vries and my car plate is 65MTND.",

    "Can you reserve a spot at Schiphol P3 Long Parking for 10 April 2026 from 06:00 to 14:00? Name: Laura Jansen, plate: KT870H.",

    "I need parking at Schiphol P4 Basic Parking on 12 April 2026 from 08:00 to 18:00. Name is Mark Peters, plate 83NRJ2.",

    "Please book Schiphol P6 Valet Parking from 6 April 2026 06:30 to 15:30. My name is Chris Meijer and my plate is 65MTPB.",

    "Reserve a parking spot at Schiphol P2 Long Parking from 7 April 2026 11:00 to 21:00. Name: Anna de Jong, plate: HN071F.",

    "I want to make a reservation at Schiphol P1 Short Parking on 9 April 2026 from 13:00 to 20:00. Name: Sophie Kramer, plate 4ZHZ18.",

    "Book parking at Schiphol P3 Long Parking from 3 April 2026 07:45 to 5 April 2026 14:00. My name is Pieter Bakker and my plate is 65MTNF.",

    "I need a parking reservation at Schiphol P4 Basic Parking from 8 April 2026 09:00 to 9 April 2026 12:00. Name: Mark Smit, plate 65MTNG.",

    "Please reserve a spot at Schiphol P1 Short Parking on 4 April 2026 from 10:00 to 19:00. Name Lisa Visser, plate 65MTNH.",

    "I want to book parking at Schiphol P6 Valet Parking on 10 April 2026 from 05:30 to 14:00. Name Ruben van Leeuwen, plate 65MTNL.",

    "Book a parking space at Schiphol P3 Long Parking from 13 April 2026 10:00 to 14 April 2026 11:00. Name Lars Hoekstra, plate 65MTNT.",

    "Reserve Schiphol P4 Basic Parking from 14 April 2026 09:15 to 18:00. Name Femke Verhoeven, plate 65MTNV.",

    "I want to make a booking at Schiphol P1 Short Parking from 12 April 2026 07:00 to 16:00. Name Noor van den Berg, plate PT255H.",

    "Please book parking at Schiphol P3 Long Parking from 11 April 2026 08:30 to 17:30. Name Daan Meijer, plate KT870H.",

    "Reserve a spot at Schiphol P6 Valet Parking from 15 April 2026 06:00 to 13:00. Name Joris Mulder, plate 83NRJ2.",

    # Slightly messy / realistic inputs
    "hey i need parking at schiphol p3 on april 10 from morning like 8 until 2pm name is anna de vries plate is 65MTND",

    "book me a spot at schiphol p1 tomorrow from 9 to 5 my name is tom jansen plate 65MTNF",

    "i want parking schiphol p4 8 april 9:00 to next day 12:00 name mark plate 65MTNG"
]
