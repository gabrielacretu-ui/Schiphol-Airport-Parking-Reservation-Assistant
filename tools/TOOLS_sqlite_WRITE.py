from typing import Optional

from langchain_classic.tools import tool
from sympy.integrals.risch import residue_reduce

from functions.FUNCTIONS_SANITIZE_input import validate, check_plate, standardize_dutch_name
from functions.FUNCTION_helpers_READ_tools import check_car_overlap, get_reservations_by_specifics
from functions.FUNCTION_helpers_WRITE_tools import validate_make_reservation_smart, \
    validate_cancel_reservation_interactive, validate_modify_parking_reservation
from INITIALIZATION_sqlite_db import get_sqlite_connection
from datetime import datetime

@tool
def validate_reservation_tool(car_number:str,customer_name:str,parking_location:str,start_time:datetime,end_time:datetime) -> dict:
    """
    Validate a new parking reservation before admin approval.

    Steps performed:
    - Validate Dutch car plate format using RDW.
    - Standardize customer name according to Dutch conventions.
    - Validate parking location against the database, including fuzzy matches.
    - Check availability at the requested parking location.
    - Check for overlapping reservations for the car.

    Args:
        car_number (str): License plate, e.g., "AZ-07-ZOL".
        customer_name (str): Full customer name, e.g., "Gabriela".
        parking_location (str): Parking location, e.g., "Schiphol P1 Short Parking".
        start_time (datetime): Reservation start datetime.
        end_time (datetime): Reservation end datetime.

    Returns:
        dict: Validation result with fields:
            - status: 'success', 'full', or 'error'
            - message: Explanation or error message
            - operation: 'making'
            - reservation info if validated
    """
    if start_time:
        start_time = start_time.strftime("%Y-%m-%d %H:%M")
    if end_time:
        end_time = end_time.strftime("%Y-%m-%d %H:%M")
    conn = get_sqlite_connection()

    try:
        # Validate location against DB using your validate() function
        validated_plate=check_plate(car_number)
        if validated_plate['status']=="error":
            return{
                "status": "error",
                "message": f"The car plate '{car_number}' is invalid.",

            }
        car_number=validated_plate['car_number']
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
        parking_location= validated_location  # replace with canonical DB value
        customer_name=standardize_dutch_name(customer_name)
        result = validate_make_reservation_smart(conn,
                                                 customer_name=customer_name,
                                                 car_number=car_number,
                                                 location=parking_location,
                                                 start_time=start_time,
                                                 end_time=end_time)
        result["operation"] = "making"
        check_overlap=check_car_overlap(conn,result["operation"], result["car_number"], result["start_time"], result["end_time"])
        if check_overlap.get('status')=="error":
            return check_overlap
        return result
    finally:
        conn.close()

@tool
def validate_cancellation_tool(car_number: str,
        customer_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        parking_location: Optional[str] = None
) -> dict:
    """
    Validate a parking reservation cancellation before admin approval.

    Steps performed:
    - Validate Dutch car plate format using RDW.
    - Retrieve existing reservations for the car.
    - Validate optional fields (customer name, parking location, times).
    - Return structured result indicating which reservations can be cancelled.

    Only the car_number is required; other fields are optional to filter cancellations.

    Args:
        car_number (str): License plate, e.g., "AZ-07-ZOL".
        customer_name (str, optional): Customer name to filter.
        parking_location (str, optional): Parking location to filter.
        start_time (datetime, optional): Filter by reservation start time.
        end_time (datetime, optional): Filter by reservation end time.

    Returns:
        dict: Validation result with fields:
            - status: 'success', 'multiple_found', or 'error'
            - message: Explanation or error message
            - operation: 'cancelling'
            - reservation_ids: IDs of reservations that match filters
    """
    if start_time:
        start_time = start_time.strftime("%Y-%m-%d %H:%M")
    if end_time:
        end_time = end_time.strftime("%Y-%m-%d %H:%M")
    conn = get_sqlite_connection()

    try:
        validated_plate = check_plate(car_number)
        if validated_plate['status'] == "error":
            return {
                "status": "error",
                "message": f"The car plate '{car_number}' is invalid.",

            }

        car_number=validated_plate['car_number']
        print(car_number)

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
                return{
                    "status": "error",
                    "message":f"Just to confirm did you mean '{validated_name}'?",
                }
            customer_name = validated_name
        print(customer_name)
        print(car_number)
        reservations_data = get_reservations_by_specifics(conn, car_number=car_number,customer_name=customer_name,parking_location=parking_location,start_time=start_time,end_time=end_time)
        if reservations_data.get("status") == "error":
            return reservations_data

        if len(reservations_data.get("reservations")) > 1:
            return {
                "status": "error",
                "message": "More than one reservations found. Please choose one  or specify the ones you want to cancel",
                "suggested_reservations": reservations_data
            }
        reservations=reservations_data.get("reservations")[0]

        result= validate_cancel_reservation_interactive(
            conn,
            car_number=reservations.get("car_number"),
            customer_name=reservations.get("customer_name"),
            parking_location=reservations.get("parking_location"),
            start_time=reservations.get("start_time"),
            end_time=reservations.get("end_time"),
        )
        result["operation"] = "cancelling"
        print(result)
        return result
    finally:
        conn.close()

@tool
def validate_modification_tool(car_number: str,
        customer_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        parking_location: Optional[str] = None,
        new_customer_name: Optional[str] = None,
        new_start_time: Optional[datetime] = None,
        new_end_time: Optional[datetime] = None,
        new_parking_location: Optional[str] = None,
) -> dict:
    """
        Validate a request to modify an existing parking reservation.

        The tool checks whether the requested changes are valid before sending
        them for admin approval.

        Args:
            car_number (str): License plate number used to identify the reservation.
            customer_name (str, optional): Name of the customer associated with the reservation.
            start_time (datetime, optional): Current reservation start time.
            end_time (datetime, optional): Current reservation end time.
            parking_location (str, optional): Current parking location.
            new_customer_name (str, optional): Updated customer name.
            new_start_time (datetime, optional): Updated reservation start time.
            new_end_time (datetime, optional): Updated reservation end time.
            new_parking_location (str, optional): Updated parking location.

        Returns:
            dict: Validation result containing status, message, operation, and relevant data.

        Notes:
            Only `car_number` is required. Optional fields are validated if provided.
            The tool also checks for overlapping reservations and may suggest corrections.
         """
    if start_time:
        start_time = start_time.strftime("%Y-%m-%d %H:%M")
    if end_time:
        end_time = end_time.strftime("%Y-%m-%d %H:%M")
    if new_start_time:
        new_start_time = new_start_time.strftime("%Y-%m-%d %H:%M")
    if new_end_time:
        new_end_time = new_end_time.strftime("%Y-%m-%d %H:%M")
    conn = get_sqlite_connection()


    try:
        validated_plate = check_plate(car_number)
        if validated_plate['status'] == "error":
            return {
                "status": "error",
                "message": f"The car plate '{car_number}' is invalid.",

            }

        car_number = validated_plate['car_number']
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
        # Validate new fields if provided
        if new_parking_location:
            validated_location = validate(conn, new_parking_location, "location", "parking_spaces")
            if not validated_location:
                # No match: suggest available locations
                cursor = conn.cursor()
                cursor.execute("SELECT location FROM parking_spaces")
                rows = cursor.fetchall()
                return {
                    "status": "error",
                    "message": f"New parking location '{new_parking_location}' not found.",
                    "available_locations": [r[0] for r in rows]
                }
            elif validated_location.lower() != new_parking_location.lower():
                # Fuzzy match adjustment
                return {
                    "status": "error",
                    "message": f"Just to confirm, did you mean '{validated_location}' for the new parking location?",
                    "suggested_location": validated_location
                }
            new_parking_location = validated_location

        # Validate new fields if provided
        if new_parking_location:
            validated_location = validate(conn, new_parking_location, "location", "parking_spaces")
            if not validated_location:
                # No match: suggest available locations
                cursor = conn.cursor()
                cursor.execute("SELECT location FROM parking_spaces")
                rows = cursor.fetchall()
                return {
                    "status": "error",
                    "message": f"New parking location '{new_parking_location}' not found.",
                    "available_locations": [r[0] for r in rows]
                }
            elif validated_location.lower() != new_parking_location.lower():
                # Fuzzy match adjustment
                return {
                    "status": "error",
                    "message": f"Just to confirm, did you mean '{validated_location}' for the new parking location?",
                    "suggested_location": validated_location
                }
            new_parking_location = validated_location

        if new_customer_name:
            new_customer_name = standardize_dutch_name(new_customer_name)


        reservations_data = get_reservations_by_specifics(conn, car_number=car_number, customer_name=customer_name,
                                                          parking_location=parking_location)

        if reservations_data.get("status") == "error":
            return reservations_data
        if len(reservations_data.get("reservations")) > 1:
            return {
                "status": "error",
                "message": "More than one reservations found. Please choose one  or specify the ones you want to modify",
                "suggested_reservations": reservations_data
            }
        reservations = reservations_data.get("reservations")[0]
        if not new_customer_name:
            new_customer_name = reservations["customer_name"]
        if not new_start_time:
            new_start_time = reservations["start_time"]
        if not new_end_time:
            new_end_time = reservations["end_time"]
        if not new_parking_location:
            new_parking_location = reservations["location"]


        result=validate_modify_parking_reservation(
            conn,
            car_number=reservations["car_number"],
            customer_name=reservations["customer_name"],
            parking_location=reservations["location"],
            start_time=reservations["start_time"],
            end_time=reservations["end_time"],
            new_customer_name=new_customer_name,
            new_location=new_parking_location,
            new_start_time=new_start_time,
            new_end_time=new_end_time
        )
        print(result)

        if result["status"] == "error":
            return result
        result["operation"] = "modifying"
        print(result["operation"])
        check_overlap = check_car_overlap(conn, result["operation"],result['car_number'], result["new_start_time"], result["new_end_time"],result["ids"])
        if check_overlap.get('status') == "error":
            result['status'] = "error"
            return check_overlap
        return result
    finally:
        conn.close()
