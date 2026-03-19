from functions.FUNCTION_helpers_READ_tools import get_reservations_by_specifics
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