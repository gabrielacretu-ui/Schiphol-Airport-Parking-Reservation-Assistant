# FUNCTION_helpers_WRITE_tools: Functions that perform write operations on the database,
# such as creating, modifying, or cancelling a reservation. Some also perform read-only
# checks to validate the reservation before executing changes. All support tool integration.

from functions.FUNCTION_helpers_READ_tools import get_available_spots, get_reservations_by_specifics


# ---------------------------------------------------
# Step 9: Make reservation (smart logic)
# ---------------------------------------------------
def validate_make_reservation_smart(conn, customer_name, car_number, location, start_time, end_time):
    """
        Validate if a reservation can be made.

        Checks parking availability for the given location and time.
        If full, suggests alternative parking locations.

        Parameters:
            conn: Database connection.
            customer_name (str): Customer name.
            car_number (str): Car identifier.
            location (str): Parking location.
            start_time: Start time.
            end_time: End time.

        Returns:
            dict: Success with reservation data, or alternatives if full.
    """

    cursor = conn.cursor()

    # -------- CHECK PARKING --------

    cursor.execute("""
        SELECT id, location
        FROM parking_spaces
        WHERE location = ?
    """, (location,))

    parking = cursor.fetchone()

    parking_id = parking["id"]
    location_name = parking["location"]
    available_slots = get_available_spots(conn, location_name, start_time, end_time)["available_slots"]

    # -------- RESERVE IF AVAILABLE --------

    if available_slots > 0:
        return {
            "status": "success",
            "customer_name": customer_name,
            "car_number":car_number,
            "location": location,
            "start_time": start_time,
            "end_time": end_time,
            "parking_id": parking_id,
        }

    # -------- IF FULL -> SUGGEST ALTERNATIVES --------

    cursor.execute("""
        SELECT 
            p.id,
            p.location,
            p.total_slots - COUNT(r.id) AS available_slots
        FROM parking_spaces p
        LEFT JOIN reservations r
            ON p.id = r.parking_id
            AND r.start_time < ?
            AND r.end_time > ?
        GROUP BY p.id
        HAVING available_slots > 0
    """, (end_time, start_time))

    alternatives = cursor.fetchall()

    if not alternatives:
        return {
            "status": "error",
            "message": "Sorry, no parking slots are currently available anywhere."
        }

    alt_list = []

    for alt in alternatives:
        alt_list.append({
            "parking_id": alt["id"],
            "location": alt["location"],
            "available_slots": alt["available_slots"]
        })

    return {
        "status": "full",
        "message": "Requested parking is full.",
        "alternatives": alt_list
    }
def make_reservation_smart(conn, customer_name, car_number, location, start_time, end_time,parking_id):
    """
        Create a new reservation in the database.

        Parameters:
            conn: Database connection.
            customer_name (str): Customer name.
            car_number (str): Car identifier.
            location (str): Parking location.
            start_time: Start time.
            end_time: End time.
            parking_id (int): Parking location ID.

        Returns:
            dict: Confirmation message if reservation is created.
    """
    cursor = conn.cursor()

    cursor.execute("""
            INSERT INTO reservations
            (customer_name, car_number, parking_id, start_time, end_time)
            VALUES (?, ?, ?, ?, ?)
        """, (customer_name, car_number, parking_id, start_time, end_time))
    conn.commit()

    return {
       "status": "success",
        "message": f"Reservation confirmed for {customer_name} at {location} from {start_time} to {end_time}."
    }


def validate_cancel_reservation_interactive(
    conn,
    car_number,
    customer_name=None,
    parking_location=None,
    start_time=None,
    end_time=None
):
    """
    Validate which reservation(s) can be canceled.

    Filters reservations by car number and optional fields.
    Returns matching reservation IDs or asks for more details if multiple found.

    Parameters:
        conn: Database connection.
        car_number (str): Car identifier.
        customer_name (str): Optional customer name.
        parking_location (str): Optional location.
        start_time: Optional start time.
        end_time: Optional end time.

    Returns:
        dict: Matching reservation IDs or multiple options.
    """
    # -------- FETCH RESERVATIONS USING EXISTING FUNCTION --------
    reservations_result = get_reservations_by_specifics(conn,car_number=car_number)

    if reservations_result["status"] != "success":
        # No reservations found
        return reservations_result

    all_reservations = reservations_result["reservations"]

    # -------- FILTER MATCHES --------
    filtered = []
    ids=[]
    for r in all_reservations:
        match = True
        if customer_name and r["customer_name"] != customer_name:
            match = False
        if parking_location and r["location"] != parking_location:
            match = False
        if start_time and r["start_time"] != start_time:
            match = False
        if end_time and r["end_time"] != end_time:
            match = False
        if match:
            filtered.append(r)
            ids.append(r["id"])

    cursor = conn.cursor()

    # -------- PERFECT MATCH → DELETE --------
    if filtered:
        return {
            "status": "success",
            "customer_name": customer_name,
            "car_number": car_number,
            "location": parking_location,
            "start_time": start_time,
            "end_time": end_time,
            "reservation_ids": ids,
        }

    # -------- MULTIPLE OPTIONS --------
    options = []
    for r in all_reservations:
        options.append({
            "customer_name": r["customer_name"],
            "location": r["location"],
            "start_time": r["start_time"],
            "end_time": r["end_time"]
        })

    return {
        "status": "multiple_found",
        "message": "Multiple reservations found. Please specify which one to cancel.",
        "reservations": options
    }
def cancel_reservation_interactive(
    conn,
    car_number,
    customer_name=None,
    parking_location=None,
    start_time=None,
    end_time=None,
    ids=None
):
    """
    Cancel one or more reservations by ID.

    Parameters:
        conn: Database connection.
        car_number (str): Car identifier.
        ids (list): List of reservation IDs to cancel.
        customer_name: Optional customer name.
        parking_location: Optional location.
        start_time: Optional start time.
        end_time: Optional filters.

    Returns:
        dict: Confirmation message with number of cancelled reservations.
    """
    print("Cancelling reservations with IDs:", ids)
    cursor=conn.cursor()
    for id1 in ids:
        cursor.execute(
                "DELETE FROM reservations WHERE id = ?",
                (id1,)  # Note: use actual reservation ID
            )

    conn.commit()

    return {
            "status": "success",
            "message": f"{len(ids)} reservation(s) cancelled for car {car_number}."
        }

