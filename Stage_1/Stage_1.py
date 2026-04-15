from langchain_classic.memory import ConversationBufferMemory
from datetime import datetime

from app.AGENT_CHATBOT import agent_chatbot
from app.GUARD_RAILS import sanitize_input_nl

from functions.FUNCTION_helpers_READ_tools import auto_release_expired_reservations
from INITIALIZATION_sqlite_db import get_sqlite_connection
from tools.TOOLS_sqlite_READ import check_availability_tool, check_existing_reservation_tool, \
    get_parking_locations_tool, estimate_parking_price_tool, get_parking_information_tool
from tools.TOOLS_sqlite_WRITE import validate_make_reservation_tool, validate_cancellation_tool, validate_modification_tool
from tools.TOOLS_weaviate import search_parking_information_tool

# ---------------------------------------------------
# LLM & Agents
# ---------------------------------------------------
chatbot_tools = [search_parking_information_tool,validate_make_reservation_tool,validate_cancellation_tool,validate_modification_tool,check_availability_tool,check_existing_reservation_tool,get_parking_information_tool,get_parking_locations_tool,estimate_parking_price_tool]

chatbot_memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )
chatbot_executor = agent_chatbot(chatbot_tools, chatbot_memory)


# ---------------------------------------------------
# Interactive loop: Chatbot + Admin interaction
# ---------------------------------------------------
def run_interactive():
    """
       Run an interactive terminal session with the parking reservation chatbot.

       This function:
       - Connects to the SQLite database.
       - Automatically releases expired reservations.
       - Continuously prompts the user for input.
       - Prepends current date/time to the input for context.
       - Sends the input to the chatbot agent for processing.
       - Displays the agent's response.
       - Exits cleanly if the user types "exit" or "quit".
       """
    conn=get_sqlite_connection()
    auto_release_expired_reservations(conn)


    print("=== Parking Reservation Chatbot ===")
    print("Type 'exit' to quit.")


    while True:
        # Ask user for input
        user_input = input("\nYou: ").strip()
        #user_input = sanitize_input_nl(user_input)  # mask sensitive info
        user_input = sanitize_input_nl(user_input)

        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        # Step 1: get current date and time dynamically (to the minute)
        now_str = datetime.now().strftime("%d-%m-%Y %H:%M")  # e.g., 15-03-2026 17:23

        # Step 2: prepend current date/time info to user input
        input_with_datetime = f"Today is {now_str}. {user_input}"

        # Step 3: send to agent
        try:
            response = chatbot_executor.invoke({"input": input_with_datetime})
            output = response.get("output", "")
        except Exception as e:
            output = f"Error: {e}"

        # Print agent's response
        print(f"Agent: {output}")

def run_automated_chatbot(questions):
    """
        Run an automated test of the chatbot with a predefined list of questions.

        Args:
            questions (list[str]): List of user inputs to send to the chatbot.

        This function:
        - Connects to the SQLite database.
        - Automatically releases expired reservations.
        - Iterates through each question.
        - Prepends current date/time to the input.
        - Sends the input to the chatbot agent for processing.
        - Prints the agent's responses.
        """
    print("=== Automated Parking Reservation Chatbot Test ===")



    conn = get_sqlite_connection()
    auto_release_expired_reservations(conn)


    for user_input in questions:
        print(f"\nYou: {user_input}")
        # Step 1: get current date and time dynamically (to the minute)
        now_str = datetime.now().strftime("%d-%m-%Y %H:%M")  # e.g., 15-03-2026 17:23

        # Step 2: prepend current date/time info to user input
        input_with_datetime = f"Today is {now_str}. {user_input}"

        # Step 3: send to agent
        try:
            response = chatbot_executor.invoke({"input": input_with_datetime})
            output = response.get("output", "")
        except Exception as e:
            output = f"Error: {e}"

        # Print agent's response
        print(f"Agent: {output}")
    print("=== End Automated Parking Reservation Chatbot Test ===")


if __name__ == "__main__":
    conn = get_sqlite_connection()
    auto_release_expired_reservations(conn)
    tests=[
    # 1. Check Existing Reservation - Normal Usage
    "Does car 6XTN75 have a reservation?",
    "Check if Jan de Vries has a reservation.",
    "Show all reservations for parking Schiphol P6 Valet Parking on 2026-04-15.",

    # 2. Check Existing Reservation - Edge Cases
    "Does 6XTN45 have any upcoming reservations?",  # multiple-day reservation
    "Check Pieter Bakker’s reservation from April 3 to April 5, 2026.",  # multi-day
    "Does Sanne van Dijk have a reservation?",  # name with prefix
    "Does 6XTN99 have a reservation?",  # no reservations

    # 3. Check Existing Reservation - Invalid Inputs
    "Check reservation for 123XYZ.",  # invalid plate
    "Does John Doe have a reservation?",  # invalid customer
    "Check reservations from 2026-15-04 08:00.",  # invalid date format

    # 4. Check Parking Availability - Normal Usage
    "Is Schiphol P1 Short Parking available on April 1, 2026?",
    "How many spots are free in P3 Long Parking today?",

    # 5. Check Parking Availability - Edge Cases
    "Check availability for P6 Valet Parking on April 15, 2026.",  # fully booked
    "Is P4 Basic Parking free from April 3 07:45 to April 3 12:00?",  # overlapping
    "Check P1 Short Parking from 18:00 to 08:00.",  # start > end

    # 6. Check Parking Availability - Invalid Inputs
    "Is P9 Ultra Parking available?",  # invalid location
    "Check availability April 35, 2026.",  # invalid date

    # 7. Get Parking Locations - Normal Usage
    "List all parking locations.",
    "Which parkings are available for long-term parking?",

    # 8. Get Parking Locations - Edge Cases
    "Show parkings with capacity more than 500.",
    "Show parkings with price less than 5€/hour.",

    # 9. Get Parking Locations - Invalid Inputs
    "Show me parking at Moon Base.",

    # 10. Validate Reservation - Normal Usage
    "Validate reservation for car 6XTN75 from April 15 06:00 to 13:00 at P6 Valet Parking for Joris Mulder.",

    # 11. Validate Reservation - Edge Cases
    "Validate reservation for 6XTN75 from April 15 12:00 to 14:00 at P6 Valet Parking.",  # overlap
    "Validate reservation at P6 Valet Parking on April 15 2026 with 151 cars.",  # max capacity
    "Validate reservation for ABC123 at P1 Short Parking.",  # invalid plate
    "Validate reservation for Jane Doe at P1 Short Parking.",  # invalid customer
    "Validate reservation from April 16 18:00 to 08:00 April 15.",  # start after end

    # 12. Get Parking Information - Normal Usage
    "What is the price of P1 Short Parking?",
    "How many spots does P3 Long Parking have?",

    # 13. Get Parking Information - Edge Cases
    "Get information for multiple locations: P1 Short Parking, P4 Basic Parking.",
    "Get information for a parking location that doesn’t exist.",

    # 14. Multi-Step / Chained Questions
    "Does 6XTN75 have a reservation? If yes, how long is it, and is P6 Valet Parking available after it ends?",
    "Check reservations for Sanne van Dijk, then validate a new reservation at P3 Long Parking from 2026-04-02 18:00 to 20:00.",
    "Show me all cars parked at P4 Basic Parking on April 3 and their customer names.",
    "Validate reservation for car 6XTN43 for P6 Valet Parking at the same time as Tom Jansen’s existing reservation.",

    # 15. Dutch-specific Name Tests
    "Does Eva van der Meer have a reservation?",
    "Does Noor van den Berg have a reservation?",
    "Check reservation for joris mulder",  # lowercase

    # 16. Car Plate Edge Cases
    "Check 65MTND reservation.",
    "Check 65MTNF reservation.",
    "Check 6XTN57 reservation vs 6XTN75.",  # similar plates
    "Check 123ABC reservation.",  # invalid plate

]
    run_interactive()
