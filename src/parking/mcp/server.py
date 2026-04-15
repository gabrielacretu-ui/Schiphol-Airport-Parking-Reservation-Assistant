"""
FastMCP server — parking reservation tools.

Run as a subprocess (invoked by router.py via MCP stdio protocol):
    python -m parking.mcp.server
"""

import os
import requests
from datetime import datetime
from typing import Optional, List

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from ..database import get_connection
from ..services import (
    make_reservation_smart,
    cancel_reservation_interactive,
    modify_parking_reservation,
)

load_dotenv()

FASTAPI_KEY = os.getenv("FASTAPI_KEY", "supersecret123")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000")

mcp = FastMCP("Parking Reservation MCP Server")


# =========================================================
# SHARED HELPER — sends confirmed event to REST API
# =========================================================
def send_event(event: dict):
    url = f"{MCP_SERVER_URL}/reservation-events-approved"
    headers = {"x-api-key": FASTAPI_KEY}
    try:
        response = requests.post(url, json=event, headers=headers, timeout=5)
        return response.json()
    except Exception as e:
        return {"status": "error", "message": f"Failed to send to REST API: {e}"}


# =========================================================
# TOOL 1 — MAKE RESERVATION
# =========================================================
@mcp.tool()
def make_reservation(
    customer_name: str,
    car_number: str,
    location: str,
    start_time: str,
    end_time: str,
    parking_id: Optional[int] = None,
) -> dict:
    conn = get_connection()
    make_reservation_smart(
        conn,
        customer_name=customer_name,
        car_number=car_number,
        location=location,
        start_time=start_time,
        end_time=end_time,
        parking_id=parking_id,
    )
    conn.commit()
    conn.close()

    event = {
        "operation": "MAKE",
        "customer_name": customer_name,
        "car_number": car_number,
        "start_time": start_time,
        "end_time": end_time,
        "approval_time": datetime.utcnow().isoformat(),
    }
    send_event(event)
    return {"status": "success", "event": event}


# =========================================================
# TOOL 2 — CANCEL RESERVATION
# =========================================================
@mcp.tool()
def cancel_reservation(
    customer_name: str,
    car_number: str,
    location: str,
    start_time: str,
    end_time: str,
    reservation_ids: Optional[List[int]] = None,
) -> dict:
    conn = get_connection()
    cancel_reservation_interactive(
        conn,
        customer_name=customer_name,
        car_number=car_number,
        parking_location=location,
        start_time=start_time,
        end_time=end_time,
        ids=reservation_ids,
    )
    conn.commit()
    conn.close()

    event = {
        "operation": "CANCEL",
        "customer_name": customer_name,
        "car_number": car_number,
        "start_time": start_time,
        "end_time": end_time,
        "approval_time": datetime.utcnow().isoformat(),
    }
    send_event(event)
    return {"status": "cancelled", "event": event}


# =========================================================
# TOOL 3 — MODIFY RESERVATION
# =========================================================
@mcp.tool()
def modify_reservation(
    customer_name: str,
    car_number: str,
    parking_location: str,
    start_time: str,
    end_time: str,
    new_customer_name: Optional[str] = None,
    new_parking_location: Optional[str] = None,
    new_start_time: Optional[str] = None,
    new_end_time: Optional[str] = None,
    ids: Optional[List[int]] = None,
    new_parking_id: Optional[int] = None,
) -> dict:
    conn = get_connection()
    modify_parking_reservation(
        conn,
        customer_name=customer_name,
        car_number=car_number,
        parking_location=parking_location,
        start_time=start_time,
        end_time=end_time,
        new_customer_name=new_customer_name,
        new_parking_location=new_parking_location,
        new_start_time=new_start_time,
        new_end_time=new_end_time,
        ids=ids,
        new_parking_id=new_parking_id,
    )
    conn.commit()
    conn.close()

    event = {
        "operation": "MODIFY",
        "customer_name": customer_name,
        "car_number": car_number,
        "start_time": start_time,
        "end_time": end_time,
        "approval_time": datetime.utcnow().isoformat(),
    }
    send_event(event)
    return {"status": "modified", "event": event}




# =========================================================
# ENTRY POINT — only when run as subprocess
# =========================================================
if __name__ == "__main__":
    mcp.run(transport="stdio")
