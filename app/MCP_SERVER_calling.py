import requests
import os
from dotenv import load_dotenv

from functions.FUNCTION_helpers_WRITE_tools import make_reservation_smart, cancel_reservation_interactive
from INITIALIZATION_sqlite_db import get_sqlite_connection

load_dotenv()

FASTAPI_KEY = os.getenv("FASTAPI_KEY", "supersecret123")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000")


def save_reservation_to_mcp_server(data: dict) -> dict:
    """
    Send reservation data to the MCP server and handle local reservation logic.

    Depending on the operation, this function either makes a new reservation
    or cancels an existing one in the local SQLite database, then sends the
    reservation data to the MCP server via a POST request.

    Parameters:
        data (dict): Reservation information, including:
            - operation: "making" or "cancelling"
            - customer_name, car_number, start_time, end_time
            - location / parking_id
            - reservation_ids (for cancelling)

    Returns:
        dict: MCP server response JSON, or an error message if the request fails.
    """
    # Call reservation logic if 'making' operation
    conn=get_sqlite_connection()
    if  data.get("operation")=="making":
        make_reservation_smart(
            conn,
            customer_name=data.get("customer_name"),
            car_number=data.get("car_number"),
            location=data.get("location"),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            parking_id=data.get("parking_id")
        )
    if data.get("operation") == "cancelling":
       cancel_reservation_interactive(
        conn,
        customer_name=data.get("customer_name"),
        car_number=data.get("car_number"),
        parking_location=data.get("location"),
        start_time=data.get("start_time"),
        end_time=data.get("end_time"),
        ids=data.get("reservation_ids")
      )
    conn.commit()
    url = f"{MCP_SERVER_URL}/reservation-events-approved"
    headers = {"x-api-key": FASTAPI_KEY}
    print(url)
    try:
        response = requests.post(url, json=data, headers=headers, timeout=5)
        return response.json()
    except Exception as e:
        return {"status": "error", "message": f"Failed to send to MCP server: {e}"}