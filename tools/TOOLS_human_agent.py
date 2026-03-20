from functions.FUNCTION_helpers_READ_tools import get_reservations_by_specifics, get_available_spots
from INITIALIZATION_sqlite_db import get_sqlite_connection
from datetime import datetime, timedelta
from langchain_core.tools import tool


def parse_datetime(dt_str: str):
    """
    Safely parse a datetime string in multiple formats.

    Parameters:
        dt_str (str): Datetime string (ISO or "%Y-%m-%d %H:%M").

    Returns:
        datetime: Parsed datetime object.
    """
    try:
        return datetime.fromisoformat(dt_str.replace("T", " "))
    except Exception:
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M")


@tool
def check_car_reservation_history_tool(car_number: str, max_active: int = 9):
    """
    Check if a car exceeds the maximum number of active reservations.

    Parameters:
        car_number (str): License plate of the car.
        max_active (int): Maximum allowed active reservations.

    Returns:
        dict: 'approved' if under limit, 'refused' if exceeded.
    """

    conn = get_sqlite_connection()

    existing = get_reservations_by_specifics(conn, car_number=car_number)
    active_count = len(existing.get("reservations", []))

    if active_count >= max_active:
        return {
            "status": "refused",
            "message": f"Car {car_number} already has {active_count} active reservations."
        }

    return {
        "status": "approved",
        "message": "No conflicts detected."
    }


@tool
def check_advance_booking_tool(reservation_start_time: str, max_days_ahead: int = 30):
    """
     Validate that the reservation is not booked too far in advance.

     Parameters:
         reservation_start_time (str): Start time of reservation.
         max_days_ahead (int): Maximum days allowed in advance.

     Returns:
         dict: 'approved' if within allowed timeframe, 'refused' otherwise.
     """

    now = datetime.now()
    start = parse_datetime(reservation_start_time)

    if start > now + timedelta(days=max_days_ahead):
        return {
            "status": "refused",
            "message": "Booking too far in advance."
        }

    return {
        "status": "approved",
        "message": "Booking within allowed timeframe."
    }


@tool
def check_reservation_length_tool(start_time: str, end_time: str, min_hours: int = 1, max_days: int = 14):
    """
      Validate that reservation duration is within allowed limits.

      Parameters:
          start_time (str): Reservation start time.
          end_time (str): Reservation end time.
          min_hours (int): Minimum reservation length in hours.
          max_days (int): Maximum reservation length in days.

      Returns:
          dict: 'approved' if duration is valid, 'refused' if too short or too long.
      """

    start = parse_datetime(start_time)
    end = parse_datetime(end_time)

    duration_hours = (end - start).total_seconds() / 3600
    duration_days = duration_hours / 24

    if duration_hours < min_hours:
        return {
            "status": "refused",
            "message": f"Reservation is too short. Minimum is {min_hours} hour(s)."
        }

    if duration_days > max_days:
        return {
            "status": "refused",
            "message": f"Reservation is too long. Maximum is {max_days} days."
        }

    return {
        "status": "approved",
        "message": "Reservation length is valid."
    }
from typing import Optional, Any, Dict

# ----------------- TOOL 1: CHECK AVAILABILITY FOR NEW RESERVATION -----------------
@tool
def check_available_slots_creation_tool(
    start_time: str,
    end_time: str,
    parking_location: str
) -> Dict[str, Any]:
    """
    Check if parking spots are available before creating a new reservation.

    Call this tool BEFORE confirming a new reservation.

    Args:
        start_time (str): Start time of the reservation.
        end_time (str): End time of the reservation.
        parking_location (str): Desired parking location.

    Returns:
        dict: status 'approved' or 'refused' and explanatory message.
    """
    conn = get_sqlite_connection()
    res = get_available_spots(conn, parking_location, start_time, end_time)

    if res["available_slots"] == 0:
        return {
            "status": "refused",
            "message": f"No available spots at {parking_location}."
        }

    return {
        "status": "approved",
        "message": f"Spots are available at {parking_location}."
    }


# ----------------- TOOL 2: CHECK AVAILABILITY FOR MODIFYING RESERVATION -----------------
@tool
def check_available_slots_modification_tool(
    new_start_time: str,
    new_end_time: str,
    new_parking_location: str
) -> Dict[str, Any]:
    """
    Check if parking spots are available before modifying an existing reservation.

    Call this tool BEFORE confirming changes to an existing reservation.

    Args:
        new_start_time (str): New start time for the reservation.
        new_end_time (str): New end time for the reservation.
        new_parking_location (str): Desired new parking location.

    Returns:
        dict: status 'approved' or 'refused' and explanatory message.
    """
    conn = get_sqlite_connection()
    res = get_available_spots(conn, new_parking_location, new_start_time, new_end_time)

    if res["available_slots"] == 0:
        return {
            "status": "refused",
            "message": f"No available spots at {new_parking_location}."
        }

    return {
        "status": "approved",
        "message": f"Spots are available at {new_parking_location}. Reservation can be modified."
    }