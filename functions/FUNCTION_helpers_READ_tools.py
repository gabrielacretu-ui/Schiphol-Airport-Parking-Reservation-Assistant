# FUNCTION_helpers_READ_tools: functions that perform read-only operations on the database,
# returning specific results based on filters or computations after extracting data
# used as support for read-only tools.

# ---------------------------------------------------
# Step 1: Estimate parking price
# ---------------------------------------------------
import sqlite3
from datetime import datetime


def estimate_parking_price(conn, parking_location, start_time, end_time):
    """
    Estimate the parking price for a given location and time interval.

    Parameters:
        conn: Database connection.
        parking_location (str): Parking location name.
        start_time (datetime): Start time of reservation.
        end_time (datetime): End time of reservation.

    Returns:
        dict: Estimated price and total hours, or error if location not found.
    """

    # Ensure row_factory returns dict-like objects
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id as parking_id, location, price_per_hour
        FROM parking_spaces
        WHERE location = ?
    """, (parking_location,))
    res = cursor.fetchone()

    if not res:
        return {"status": "error", "message": f"Parking location '{parking_location}' not found."}

    price_per_hour = res["price_per_hour"]

    # Compute total time in hours
    total_seconds = (end_time - start_time).total_seconds()
    total_hours = total_seconds / 3600  # convert seconds to hours

    estimated_price = round(price_per_hour * total_hours, 2)

    return {
        "status": "success",
        "parking_location": parking_location,
        "total_hours": int(round(total_hours, 2)),
        "estimated_price": estimated_price
    }

# ---------------------------------------------------
# Step 2: Number of available spots
# ---------------------------------------------------
def get_available_spots(conn, location:str, start_time, end_time):
    """
    Get available parking spots for a location and time interval.

    Parameters:
        conn: Database connection.
        location (str): Parking location name.
        start_time: Start time.
        end_time: End time.

    Returns:
        dict: Total, reserved, and available slots, or error if location not found.
    """
    cursor = conn.cursor()


    # Get parking id and total capacity
    cursor.execute("""
        SELECT id, total_slots
        FROM parking_spaces
        WHERE location = ?
    """, (location,))

    row = cursor.fetchone()

    if not row:
        return {
            "status": "error",
            "message": f"Parking location '{location}' not found"
        }

    parking_id=row['id']
    total_slots = row['total_slots']

    # Count overlapping reservations
    cursor.execute("""
        SELECT COUNT(*) as reserved_count
        FROM reservations
        WHERE parking_id = ?
        AND start_time < ?
        AND end_time > ?
    """, (parking_id, end_time, start_time))

    res = cursor.fetchone()
    reserved_count = res['reserved_count']


    available = total_slots - reserved_count

    return {
        "status": "success",
        "location": location,
        "start_time": start_time,
        "end_time": end_time,
        "total_slots": total_slots,
        "reserved_slots": reserved_count,
        "available_slots": available
    }
# ---------------------------------------------------
# Step 3: Automatically release expired reservations
# ---------------------------------------------------
def auto_release_expired_reservations(conn):
    """
        Remove expired reservations from the database.

        Parameters:
            conn: Database connection.

        Returns:
            dict: Number of deleted reservations or info if none found.
        """
    cursor = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    cursor.execute("""
        DELETE FROM reservations
        WHERE end_time <= ?
    """, (now,))

    deleted_count = cursor.rowcount
    conn.commit()

    if deleted_count == 0:
        return {
            "status": "info",
            "message": "No expired reservations found."
        }

    return {
        "status": "success",
        "message": f"{deleted_count} expired reservations released."
    }

# ---------------------------------------------------
# Step 4: Associated reservations with a car
# ---------------------------------------------------
def get_reservations_by_specifics(conn, car_number: str = None, customer_name: str = None,
                                  start_time=None, end_time=None, parking_location:str=None):
    """
    Retrieve reservations based on optional filters.

    Parameters:
        conn: Database connection.
        car_number (str): Car number filter.
        customer_name (str): Customer name filter.
        start_time: Start time filter.
        end_time: End time filter.
        parking_location (str): Parking location filter.

    Returns:
        dict: Matching reservations or error if none found.
    """
    if not any([car_number, customer_name, start_time, end_time, parking_location]):
        return {
            "status": "error",
            "message": "No fields found",
            "reservations": []
        }

    cursor = conn.cursor()

    # Base query
    query = """
        SELECT 
            r.id,
            r.customer_name,
            r.car_number,
            r.parking_id,
            r.start_time,
            r.end_time,
            ps.location
        FROM reservations r
        LEFT JOIN parking_spaces ps 
        ON r.parking_id = ps.id
    """

    # Build dynamic WHERE conditions
    conditions = []
    params = []

    if car_number:
        conditions.append("r.car_number = ?")
        params.append(car_number)
    if customer_name:
        conditions.append("r.customer_name = ?")
        params.append(customer_name)
    if start_time:
        conditions.append("r.start_time >= ?")
        params.append(start_time)
    if end_time:
        conditions.append("r.end_time <= ?")
        params.append(end_time)
    if parking_location:
        conditions.append("ps.location = ?")
        params.append(parking_location)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY r.start_time"

    cursor.execute(query, tuple(params))
    reservations = cursor.fetchall()

    if not reservations:
        return {
            "status": "error",
            "message": "No reservations found for the given filters",
            "filters": {
                "car_number": car_number,
                "customer_name": customer_name,
                "start_time": start_time,
                "end_time": end_time,
                "parking_location": parking_location
            },
            "reservations": []
        }

    results = [
        {
            "id": r["id"],
            "customer_name": r["customer_name"],
            "car_number": r["car_number"],
            "parking_id": r["parking_id"],
            "location": r["location"],
            "start_time": r["start_time"],
            "end_time": r["end_time"]
        }
        for r in reservations
    ]

    return {
        "status": "success",
        "filters": {
            "car_number": car_number,
            "customer_name": customer_name,
            "start_time": start_time,
            "end_time": end_time,
            "parking_location": parking_location
        },
        "reservations": results
    }
# ---------------------------------------------------
# Step 5: Return parking locations
# ---------------------------------------------------
def get_parking_locations(conn):
    """
        Retrieve all parking locations.

        Parameters:
            conn: Database connection.

        Returns:
            dict: List of parking locations or info if none found.
        """
    cursor = conn.cursor()

    cursor.execute("SELECT id, location FROM parking_spaces")
    rows = cursor.fetchall()

    if not rows:
        return {
            "status": "info",
            "message": "No parking locations found.",
            "locations": []
        }

    locations = [{"id": r["id"], "location": r["location"]} for r in rows]

    return {
        "status": "success",
        "locations": locations
    }
# ---------------------------------------------------
# Step 6: Return car overlap
# ---------------------------------------------------
def check_car_overlap(conn, operation, car_number, start_time=None, end_time=None, ids=None) -> dict:
    """
    Check if a car has overlapping reservations.

    Parameters:
        conn: Database connection.
        operation (str): Type of operation ("making" or "modifying").
        car_number (str): Car identifier.
        start_time: Start time.
        end_time: End time.
        ids (list): Reservation IDs to exclude (for modifying).

    Returns:
        dict: Success if no overlap, otherwise error with explanation.
    """
    cur = conn.cursor()

    if not start_time or not end_time:
        return {
            "status": "error",
            "explanation": "start_time and end_time are required."
        }

    conflict = None

    if operation == "making":

        cur.execute(
            """
            SELECT start_time, end_time
            FROM reservations
            WHERE car_number = ?
            AND NOT (end_time <= ? OR start_time >= ?)
            LIMIT 1
            """,
            (car_number, start_time, end_time),
        )

        conflict = cur.fetchone()

    elif operation == "modifying":

        if ids:
            placeholders = ",".join(["?"] * len(ids))

            query = f"""
                SELECT start_time, end_time
                FROM reservations
                WHERE car_number = ?
                AND NOT (end_time <= ? OR start_time >= ?)
                AND id NOT IN ({placeholders})
                LIMIT 1
            """

            params = [car_number, start_time, end_time, *ids]

            cur.execute(query, params)

        else:

            cur.execute(
                """
                SELECT start_time, end_time
                FROM reservations
                WHERE car_number = ?
                AND NOT (end_time <= ? OR start_time >= ?)
                LIMIT 1
                """,
                (car_number, start_time, end_time),
            )

        conflict = cur.fetchone()

    if conflict:
        return {
            "status": "error",
            "explanation": f"Car {car_number} already has an overlapping reservation from {conflict['start_time']} to {conflict['end_time']}."
        }

    return {
        "status": "success",
        "explanation": "No overlapping reservations found."
    }

def get_parking_information(conn, parking_location):
    # Make sure the connection returns dictionary-like rows
    """
       Retrieve detailed information about a parking location.

       Parameters:
           conn: Database connection.
           parking_location (str): Parking location name.

       Returns:
           dict: Parking details such as slots and price per hour.
       """
    cursor = conn.cursor()

    query = "SELECT * FROM parking_spaces WHERE location = ?"
    cursor.execute(query, (parking_location,))
    rows = cursor.fetchall()

    results = [
        {
            "id": r["id"],
            "parking_location": r["location"],
            "total_slots": r["total_slots"],
            "price_per_hour": r["price_per_hour"],
        }
        for r in rows
    ]


    return {
        "status": "success",
        "parking_location": parking_location,
        "information": results
    }