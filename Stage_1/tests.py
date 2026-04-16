#here we test if the right tools are chosen so that the right results are provided

import unittest
from datetime import datetime

from parking.agents.chatbot import agent_chatbot
from parking.database import get_connection
from langchain_classic.memory import ConversationBufferMemory


class TestChatbotE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = get_connection()
        cls.chatbot_memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        from parking.tools import check_availability_tool, check_existing_reservation_tool, \
            get_parking_locations_tool, estimate_parking_price_tool, get_parking_information_tool
        from parking.tools import validate_make_reservation_tool, validate_cancellation_tool

        chatbot_tools = [
            check_availability_tool,
            check_existing_reservation_tool,
            get_parking_locations_tool,
            estimate_parking_price_tool,
            get_parking_information_tool, validate_make_reservation_tool, validate_cancellation_tool
        ]
        cls.chatbot_executor = agent_chatbot(chatbot_tools, cls.chatbot_memory)

    def ask_chatbot(self, query):
        now_str = datetime.now().strftime("%d-%m-%Y %H:%M")  # e.g., 15-03-2026 17:23

        # Step 2: prepend current date/time info to user input
        input_with_datetime = f"Today is {now_str}. {query}"

        response = self.chatbot_executor.invoke({"input":input_with_datetime})
        return response.get("output", "")

    def test_check_and_validate_overlap(self):
            answer = self.ask_chatbot(
                "Can you help me validate a a new reservation i want to Make for Jan de Vries for the car number VR295H, at Schiphol P3 Long Parking from 2026-05-01 9:00 to 20:00.")
            self.assertIn("overlap", answer)

    def test_parking_info_p1(self):
        answer = self.ask_chatbot("How many spots are in Schiphol P1 Short Parking?")
        self.assertIn("500", answer)
        self.assertIn("P1 Short Parking", answer)

    def test_estimate_price_p3(self):
        answer = self.ask_chatbot("Estimate price for Schiphol P3 Long Parking from 2026-04-19 09:15 to 2026-04-21 18:00.")
        self.assertIn("170.25", answer)  # matches your Stage 1 example
        self.assertIn("P3 Long Parking", answer)

    def test_check_reservation(self):
        answer = self.ask_chatbot("Does 6XTN75 have a reservation?")
        self.assertIn("Joris Mulder", answer)
        self.assertIn("6XTN75", answer)
# --- Reservation Tests ---
    def test_reservation_by_car(self):
        answer = self.ask_chatbot("Does 6XTN75 have a reservation?")
        self.assertIn("Joris Mulder", answer)
        self.assertIn("6XTN75", answer)

    def test_reservation_by_customer(self):
        answer = self.ask_chatbot("Check if Jan de Vries has a reservation.")
        self.assertIn("Jan de Vries", answer)
        self.assertIn("VR295H", answer)



    # --- Parking Availability Tests ---
    def test_availability_p1_short(self):
        answer = self.ask_chatbot("Is Schiphol P1 Short Parking available on April 19, 2026?")
        self.assertIn("500", answer)
        self.assertIn("Schiphol P1 Short Parking", answer)


    def test_availability_after_reservation(self):
        answer = self.ask_chatbot("Does 6XTN75 have a reservation? If yes, how long is it, and is Schiphol P6 Valet Parking available after it ends?")
        self.assertIn("7", answer)
        self.assertIn("available", answer)

    # --- Parking Information Tests ---
    def test_parking_info_p3(self):
        answer = self.ask_chatbot("How many spots does P3 Long Parking have?")
        self.assertIn("2000", answer)
        self.assertIn("P3 Long Parking", answer)

    def test_parking_price_p1(self):
        answer = self.ask_chatbot("Get the info about the fee per hour of P1 Short Parking ?")
        self.assertIn("6.50", answer)
        self.assertIn("P1 Short Parking", answer)



if __name__ == "__main__":
    unittest.main()