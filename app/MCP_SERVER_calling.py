# mcp_server.py

import asyncio
import json
import os
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import sys

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from INITIALIZATION_sqlite_db import get_sqlite_connection
from functions.FUNCTION_helpers_WRITE_tools import (
    make_reservation_smart,
    cancel_reservation_interactive,
    modify_parking_reservation,
)

load_dotenv()

FASTAPI_KEY = os.getenv("FASTAPI_KEY", "supersecret123")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000")


mcp = FastMCP("Parking Reservation MCP Server")


# =========================================================
# SHARED HELPER → sends event to REST API
# =========================================================
def send_event(event: dict):
    url = f"{MCP_SERVER_URL}/reservation-events-approved"
    headers = {"x-api-key": FASTAPI_KEY}
    try:
        response = requests.post(url, json=event, headers=headers, timeout=5)
        return response.json()
    except Exception as e:
        return {"status": "error", "message": f"Failed to send to MCP server: {e}"}


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

    conn = get_sqlite_connection()

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
        "approval_time": datetime.utcnow().isoformat()
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

    conn = get_sqlite_connection()

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
        "approval_time": datetime.utcnow().isoformat()
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

    conn = get_sqlite_connection()

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
        "approval_time": datetime.utcnow().isoformat()
    }

    send_event(event)

    return {"status": "modified", "event": event}


# =========================================================
# TOOL 4 — LIST RESERVATIONS FROM SQLITE
# =========================================================
@mcp.tool()
def list_reservations() -> dict:
    """Return all reservations joined with their parking location name."""
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.id, r.customer_name, r.car_number,
               p.location, r.start_time, r.end_time
        FROM reservations r
        JOIN parking_spaces p ON r.parking_id = p.id
        ORDER BY r.start_time
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"total": len(rows), "reservations": rows}


# =========================================================
# RUN
# =========================================================
if __name__ == "__main__":
    mcp.run(transport="stdio")


# =========================================================
# MCP CLIENT ROUTER  (only when imported, not when run as subprocess)
# =========================================================
if __name__ != "__main__":
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from langchain_core.tools import StructuredTool
    from langchain_openai import ChatOpenAI

    _MCP_SERVER_PATH = str(Path(__file__))
    _PROJECT_ROOT = str(Path(__file__).parent.parent)
    _subprocess_env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(filter(None, [_PROJECT_ROOT, os.environ.get("PYTHONPATH", "")]))
    }
    _SERVER_PARAMS = StdioServerParameters(
        command=sys.executable,
        args=[_MCP_SERVER_PATH],
        env=_subprocess_env
    )

    _mcp_tools = [
        StructuredTool.from_function(
            func=make_reservation,
            name="make_reservation",
            description="Make a new parking reservation. Use when operation is 'making'.",
        ),
        StructuredTool.from_function(
            func=cancel_reservation,
            name="cancel_reservation",
            description="Cancel an existing parking reservation. Use when operation is 'cancelling'.",
        ),
        StructuredTool.from_function(
            func=modify_reservation,
            name="modify_reservation",
            description="Modify an existing parking reservation. Use when operation is 'modifying'.",
        ),
    ]

    _router_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools(_mcp_tools)

    async def _call_mcp_tool(tool_name: str, arguments: dict):
        """Spawn this file as an MCP subprocess and call a tool over the protocol."""
        async with stdio_client(_SERVER_PARAMS) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                if result.isError:
                    raise RuntimeError(f"MCP tool '{tool_name}' failed: {[c.text for c in result.content]}")
                return result

    def route_and_execute_mcp_tool(validated_dict: dict):
        """LLM picks the correct MCP tool; execution goes through the MCP stdio protocol."""
        response = _router_llm.invoke(
            f"Execute the following reservation operation using the appropriate tool:\n{json.dumps(validated_dict)}"
        )
        if not response.tool_calls:
            print("Warning: LLM did not select a tool. No reservation action taken.")
            return
        for tool_call in response.tool_calls:
            print(f"Routing to MCP tool: {tool_call['name']} with args: {tool_call['args']}")
            asyncio.run(_call_mcp_tool(tool_call["name"], tool_call["args"]))