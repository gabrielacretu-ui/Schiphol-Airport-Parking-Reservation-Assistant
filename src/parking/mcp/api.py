# creation_mcp_server_json.py
# Run with:
# python -m uvicorn MCP_SERVER:app
# http://127.0.0.1:8000/docs

import os
from fastapi import FastAPI, Header, HTTPException
from datetime import datetime
from dotenv import load_dotenv

from ..database import get_connection

# Load environment variables
load_dotenv()

app = FastAPI()

# -------------------------------
# Configuration
# -------------------------------
FASTAPI_KEY = os.getenv("FASTAPI_KEY", "supersecret123")  # fallback
LOG_DIR = "./logs"
LOG_FILE = "confirmed_reservations_events.txt"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, LOG_FILE)

# In-memory JSON storage
confirmed_reservations = []

# -------------------------------
# Health check
# -------------------------------
@app.get("/")
def root():
    """
        Root endpoint to check server status.

        Returns a simple message indicating that the MCP reservation server is running.

        Returns:
            dict: {"status": str} server status message.
        """
    return {"status": "MCP reservation server running"}

# -------------------------------
# Save confirmed reservation
# -------------------------------
@app.post("/reservation-events-approved")
def save_confirmed_reservation_event(data: dict, x_api_key: str = Header(...)):

    if x_api_key != FASTAPI_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")


    required = ["customer_name", "car_number", "start_time", "end_time","approval_time"]
    if not all(k in data for k in required):
        raise HTTPException(status_code=400, detail="Incomplete data")


    confirmed_reservations.append(data)

    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(
            f"{data['operation']} | {data['customer_name']} | "
            f"{data['car_number']} | {data['start_time']} - {data['end_time']} | "
            f"{data['approval_time']}\n"
        )

    return {"status": "logged", "reservation": data}

# -------------------------------
# Retrieve all reservations
# -------------------------------
@app.get("/reservations")
def get_reservations(x_api_key: str = Header(...)):
    """
    Retrieve all confirmed reservations.

    Checks the API key for authorization, then returns
    the total number of reservations and the list of confirmed reservations.

    Parameters:
        x_api_key (str): API key for authorization.

    Raises:
        HTTPException: 403 if API key is invalid.

    Returns:
        dict: {
            "total_reservations": int,
            "reservations": list of reservation entries
        }
    """

    if x_api_key != FASTAPI_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")

    return {
        "total_reservations": len(confirmed_reservations),
        "reservations": confirmed_reservations
    }