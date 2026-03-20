# creation_mcp_server_json.py
# Run with:
# python -m uvicorn MCP_SERVER:app
# http://127.0.0.1:8000/docs

import os
from fastapi import FastAPI, Header, HTTPException
from datetime import datetime
from dotenv import load_dotenv

from INITIALIZATION_sqlite_db import get_sqlite_connection

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
    """
    Save an approved reservation event.

    This endpoint validates reservation data, checks the API key,
    adds the reservation to the in-memory list, and logs it to a file.

    Parameters:
        data (dict): Reservation info, including:
            - customer_name / new_customer_name
            - car_number / new_car_number
            - start_time / new_start_time
            - end_time / new_end_time
            - operation (optional)
        x_api_key (str): API key for authorization.

    Raises:
        HTTPException: 403 if API key is invalid.
        HTTPException: 400 if essential reservation fields are missing.
    """
    conn = get_sqlite_connection()

    # Check API key
    if x_api_key != FASTAPI_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")
    print(data)

    # Extract reservation data with fallback
    approval_time = datetime.now().strftime("%d-%m-%Y %H:%M")
    customer_name = data.get("new_customer_name") or data.get("customer_name")
    car_number    = data.get("new_car_number") or data.get("car_number")
    start_time    = data.get("new_start_time") or data.get("start_time")
    end_time      = data.get("new_end_time") or data.get("end_time")
    operation     = f"{data.get('operation', 'unknown')} reservation"


    # -------------------------------
    # Only log if essential fields are present
    # -------------------------------
    if not all([customer_name, car_number, start_time, end_time]):
        # Skip incomplete reservation
        print(f"Skipping logging: incomplete reservation data {data}")
        raise HTTPException(status_code=400, detail="Incomplete reservation data")

    # Append to in-memory storage
    reservation_entry = {
        "operation": operation.upper(),
        "customer_name": customer_name,
        "car_number": car_number,
        "reservation_period": f"{start_time} - {end_time}",
        "approval_time": approval_time
    }
    confirmed_reservations.append(reservation_entry)

    # Append to log file
    entry = f"{operation.upper()} | {customer_name} | {car_number} | {start_time} - {end_time} | {approval_time}\n"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(entry)



    return {"status": "saved", "reservation": reservation_entry}

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