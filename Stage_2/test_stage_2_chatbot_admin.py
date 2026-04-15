#here I tested basically if the pipeline works as expected and if the admin approves or rejects
#expected reservations

import unittest
import json
from datetime import datetime

from langchain_classic.memory import ConversationBufferMemory

from app.AGENT_ADMIN import agent_admin
from app.AGENT_CHATBOT import agent_chatbot

from INITIALIZATION_sqlite_db import get_sqlite_connection
from functions.FUNCTION_helpers_READ_tools import auto_release_expired_reservations

from tools.TOOLS_sqlite_READ import (
    check_existing_reservation_tool,
    get_parking_locations_tool,
    get_parking_information_tool, estimate_parking_price_tool, check_availability_tool
)

from tools.TOOLS_sqlite_WRITE import validate_reservation_tool

from tools.TOOLS_human_agent import (
    check_car_reservation_history_tool,
    check_advance_booking_tool,
    check_reservation_length_tool
)


class TestMultiAgentE2E(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # DB setup
        cls.conn = get_sqlite_connection()
        auto_release_expired_reservations(cls.conn)

        # Shared memory
        cls.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )


        # Tools
        chatbot_tools = [
            check_existing_reservation_tool,
            get_parking_locations_tool,
            estimate_parking_price_tool,
            get_parking_information_tool, validate_reservation_tool, check_availability_tool
        ]

        admin_tools = [
            check_reservation_length_tool,
            check_car_reservation_history_tool,
            check_advance_booking_tool
        ]

        # Executors
        cls.chatbot_executor = agent_chatbot(chatbot_tools, cls.memory)
        cls.admin_executor = agent_admin(admin_tools, cls.memory)

    # -------------------------------------------------
    # Helper: full pipeline execution
    # -------------------------------------------------
    def run_pipeline(self, user_input):
        now_str = datetime.now().strftime("%d-%m-%Y %H:%M")
        input_with_datetime = f"Always use the provided tools before answering.Today is {now_str}. {user_input}"

        try:

            chatbot_output = self.chatbot_executor.invoke({"input": input_with_datetime})

            validated_dict = None

            for action, tool_output in reversed(chatbot_output["intermediate_steps"]):
                   #print(validated_dict)
                   if action.tool.startswith("validate_"):
                       validated_dict = tool_output
                       break

        except Exception as e:
            return f"Chatbot error: {e}"

        # If no validation → return chatbot only,and validated "read-only" as no operation was made, in case the chatbot hallucinates it will be terminated before asking the admin
        if validated_dict is None:
            return  {
            "chatbot": chatbot_output.get("output"),
            "validated": "read-only",
            "admin": None
        }

        # FIRST → check if validation FAILED
        if validated_dict.get("status") != "success":
            return {
                "chatbot": chatbot_output.get("output"),
                "validated": "failed",
                "admin": None
            }



        try:

            admin_response = self.admin_executor.invoke({
                "input": json.dumps(validated_dict)
            })

            admin_result = admin_response.get("output", {})

        except Exception as e:
            return f"Admin error: {e}"


        # -----------------------------
        # Step 4: Final decision
        # -----------------------------

        return {
            "chatbot": chatbot_output.get("output"),
            "validated": validated_dict,
            "admin": admin_result
        }


    # -------------------------------------------------
    # TESTS
    # -------------------------------------------------

    def test_valid_reservation(self):
        result = self.run_pipeline(
            "I want to book a parking spot at Schiphol P1 Short Parking from 1 April 2026 09:00 to 1 April 2026 12:00. My name is Jan de Vries and my car plate is 65MTND."
        )

        self.assertIn("approve", result.get("admin").lower())


    def test_invalid_plate(self):
        result = self.run_pipeline(
            "Can you reserve a spot at Schiphol P3 Long Parking for 10 April 2026 from 06:00 to 14:00? Name: Laura Jansen, plate: AB896R2"
        )

        self.assertEqual("failed",result.get("validated"))

    def test_read_only_trigger_no_validation(self):
        result = self.run_pipeline(
            "Tell me the slots available at Schiphol P6 Valet Parking from 5PM on 1st of April to 4PM on 2nd of April"
        )

        self.assertEqual("read-only", result.get("validated"))



    def test_wrong_parking_location_trigger(self):
        result = self.run_pipeline(
            "Check if Moon Sntarini is a valid location. If yes Make reservation for HN071F from April 15 12:00 to 14:00 at Moon Santorini."
        )

        self.assertEqual("read-only", result.get("validated"))

    def test_valid_reservation_making(self):
        result = self.run_pipeline(
            "Make reservation for Jan de Vries, car number VR295H from April 18 12:00 to 14:00 at Schiphol P6 Valet Parking."
        )

        self.assertIsInstance(result.get("validated"), dict)
        self.assertIn("approve", result.get("admin").lower())

    def test_invalid_location(self):
        result = self.run_pipeline(
            "Book parking for Jan de Vries, car number V978DS "
            "from 10 April 2026 10:00 to 12:00 at Hogwarts Parking."
        )

        self.assertEqual("failed", result.get("validated"))
        self.assertIsNone(result.get("admin"))

    def test_price_inquiry_read_only(self):
        result = self.run_pipeline(
            "How much does parking cost at Schiphol P1 Short Parking for 3 hours?"
        )

        self.assertEqual("read-only", result.get("validated"))
        self.assertIsNone(result.get("admin"))

    def test_reservation_history_read_only(self):
        result = self.run_pipeline(
            "Show me all reservations for car number V976HV."
        )

        self.assertEqual("read-only", result.get("validated"))

    def test_mixed_intent_booking(self):
        result = self.run_pipeline(
            "Check availability at Schiphol P6 Valet Parking and book it "
            "for V97HBB from 12 April 2026 10:00 to 12:00."
        )

        self.assertIsInstance(result.get("validated"), dict)
        self.assertIn("approve", result.get("admin").lower())










if __name__ == "__main__":
    unittest.main()