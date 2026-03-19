# chatbot_main.py
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from functions.FUNCTIONS_SANITIZE_input import validate, standardize_dutch_name, check_plate
from INITIALIZATION_sqlite_db import (
    get_sqlite_connection,
)
from langchain_classic.tools import tool
from functions.FUNCTION_helpers_READ_tools import get_parking_locations, estimate_parking_price, get_available_spots, \
    get_reservations_by_specifics, get_parking_information

load_dotenv()
# ---------------------------------------------------
# SQLite Tool Wrappers
# ---------------------------------------------------



# -------------------------------
# Get parking locations wrapper
# -------------------------------
@tool
def get_parking_locations_tool():
    """
    Retrieve a list of all available parking locations.

    Returns:
        dict: Dictionary with 'status' and 'locations', where 'locations' is a list
              of parking location names and IDs.
    """
    conn = get_sqlite_connection()
    try:
        return get_parking_locations(conn)
    finally:
        conn.close()

# -------------------------------
# Estimate parking price wrapper
# -------------------------------
@tool
def estimate_parking_price_tool(parking_location: str,
    start_time: datetime,
    end_time: datetime) -> dict:
    """
    Estimate the price of a parking reservation for a given location and time range.

    Connects to SQLite, validates the parking location, and computes the estimated price.

    Parameters:
        parking_location (str): The name of the parking location.
        start_time (datetime): Reservation start datetime.
        end_time (datetime): Reservation end datetime.

    Returns:
        dict: 'success' with estimated price or 'error' with message and suggested locations.
    """
    conn = get_sqlite_connection()
    try:
        # Validate parking location
        if parking_location:
            validated_location = validate(conn, parking_location, "location", "parking_spaces")
            if not validated_location:
                # No match: suggest available locations
                cursor = conn.cursor()
                cursor.execute("SELECT location FROM parking_spaces")
                rows = cursor.fetchall()
                return {
                    "status": "error",
                    "message": f"Parking location '{parking_location}' not found.",
                    "available_locations": [r[0] for r in rows]
                }

            # Optional: if fuzzy match changed the location slightly, ask for confirmation
            if validated_location.lower() != parking_location.lower():
                return {
                    "status": "error",
                    "message": f"Just to confirm, did you mean '{validated_location}' for the parking location?",
                    "suggested_location": validated_location
                }
            parking_location = validated_location

        # Call estimate function
        result = estimate_parking_price(conn, parking_location, start_time, end_time)

        return result
    finally:
        conn.close()
# -------------------------------
# Check availability wrapper
# -------------------------------

@tool
def check_availability_tool(
    parking_location: str,
    start_time: datetime,
    end_time: datetime
) -> dict:
    """
    Check availability of parking spots for a given location and time range.

    Parameters:
        parking_location (str): Name of the parking lot.
        start_time (datetime): Start datetime.
        end_time (datetime): End datetime.

    Returns:
        dict: Availability information including total, reserved, and available slots.
              Returns 'error' if the location is invalid or not found.
    """
    if start_time:
        start_time = start_time.strftime("%Y-%m-%d %H:%M")
    if end_time:
        end_time = end_time.strftime("%Y-%m-%d %H:%M")

    # Normalize inputs to datetime objects if they are strings
    conn = get_sqlite_connection()
    try:
        if parking_location:
            validated_location = validate(conn, parking_location, "location", "parking_spaces")
            if not validated_location:
                # No match: suggest available locations
                cursor = conn.cursor()
                cursor.execute("SELECT location FROM parking_spaces")
                rows = cursor.fetchall()
                return {
                    "status": "error",
                    "message": f"Parking location '{parking_location}' not found.",
                    "available_locations": [r[0] for r in rows]
                }

            # Optional: if fuzzy match changed the location slightly, ask for confirmation
            if validated_location.lower() != parking_location.lower():
                return {
                    "status": "error",
                    "message": f"Just to confirm, did you mean '{validated_location}' for the parking location?",
                    "suggested_location": validated_location
                }
            parking_location = validated_location

        # Fetch available spots
        return get_available_spots(
            conn,
            location=parking_location,
            start_time=start_time,
            end_time=end_time
        )

    finally:
        conn.close()

# -------------------------------
# Check existing reservation wrapper
# -------------------------------
@tool
def check_existing_reservation_tool(
        car_number: Optional[str] = None,
        customer_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        parking_location: Optional[str] = None
) -> dict:
    """
    Check existing parking reservations based on optional filters.

    Validates input values (car plate, customer name, parking location) before querying.

    Parameters:
        car_number (str): License plate of the car.
        customer_name (str): Customer's full name.
        start_time (datetime): Filter reservations starting from this time.
        end_time (datetime): Filter reservations ending before this time.
        parking_location (str): Parking location name.

    Returns:
        dict: Matching reservations or an error message if validation fails.
    """
    if not any([car_number, customer_name, start_time, end_time, parking_location]):
        return {
            "status": "error",
            "message": "No fields found",
            "reservations": []
        }
    if start_time:
        start_time = start_time.strftime("%Y-%m-%d %H:%M")
    if end_time:
        end_time = end_time.strftime("%Y-%m-%d %H:%M")


    conn = get_sqlite_connection()
    try:
        # Validate car_number
        if car_number:
            validated_car_query=check_plate(car_number)
            if validated_car_query["status"]=="error":
                return {
                    "status": "error",
                    "message": f"The car plate is {car_number} and is an invalid Dutch plate"
                }
            validated_car=validated_car_query["car_number"]
            validated_car = validate(conn, validated_car, "car_number", "reservations")
            if not validated_car:
                return {
                    "status": "error",
                    "message": f"Car number: {car_number} not found in the database",
                    "reservations": []
                }
            car_number = validated_car

            # Validate optional fields
            if parking_location:
                validated_location = validate(conn, parking_location, "location", "parking_spaces")
                if not validated_location:
                    # No match: suggest available locations
                    cursor = conn.cursor()
                    cursor.execute("SELECT location FROM parking_spaces")
                    rows = cursor.fetchall()
                    return {
                        "status": "error",
                        "message": f"Parking location '{parking_location}' not found.",
                        "available_locations": [r[0] for r in rows]
                    }

                # Optional: if fuzzy match changed the location slightly, ask for confirmation
                if validated_location.lower() != parking_location.lower():
                    return {
                        "status": "error",
                        "message": f"Just to confirm, did you mean '{validated_location}' for the parking location?",
                        "suggested_location": validated_location
                    }
                parking_location = validated_location

            if customer_name:
                customer_name = standardize_dutch_name(customer_name)
                validated_name = validate(conn, customer_name, "customer_name", "reservations")
                if not validated_name:
                    return {
                        "status": "error",
                        "message": f"Customer name '{customer_name}' not found.",
                    }
                elif validated_name.lower() != customer_name.lower():
                    return {
                        "status": "error",
                        "message": f"Just to confirm did you mean '{validated_name}'?",
                    }
                customer_name = validated_name
        return get_reservations_by_specifics(
            conn,
            car_number=car_number,
            customer_name=customer_name,
            start_time=start_time,
            end_time=end_time,
            parking_location=parking_location
        )
    finally:
        conn.close()


@tool
def get_parking_information_tool( parking_location: str) -> dict:
    """
    Retrieve detailed information about a specific parking location.

    Parameters:
        parking_location (str): Name of the parking location.

    Returns:
        dict: Contains parking details such as:
            - status: 'success' if valid, 'error' if invalid
            - information: List with keys id, location, total_slots, price_per_hour
            - message (optional): Error description if status is 'error'
    """
    conn = get_sqlite_connection()
    validated_location = validate(conn, parking_location, "location", "parking_spaces")
    if parking_location:
        validated_location = validate(conn, parking_location, "location", "parking_spaces")
        if not validated_location:
            # No match: suggest available locations
            cursor = conn.cursor()
            cursor.execute("SELECT location FROM parking_spaces")
            rows = cursor.fetchall()
            return {
                "status": "error",
                "message": f"Parking location '{parking_location}' not found.",
                "available_locations": [r[0] for r in rows]
            }

        # Optional: if fuzzy match changed the location slightly, ask for confirmation
        if validated_location.lower() != parking_location.lower():
            return {
                "status": "error",
                "message": f"Just to confirm, did you mean '{validated_location}' for the parking location?",
                "suggested_location": validated_location
            }
        parking_location = validated_location

    return get_parking_information(conn, parking_location)


