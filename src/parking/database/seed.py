import sqlite3

from .connection import insert_row
PARKING_SPACES = [
    {"location": "Schiphol P1 Short Parking", "total_slots": 500,  "price_per_hour": 6.50},
    {"location": "Schiphol P3 Long Parking",  "total_slots": 2000, "price_per_hour": 3.00},
    {"location": "Schiphol P4 Basic Parking", "total_slots": 800,  "price_per_hour": 2.50},
    {"location": "Schiphol P6 Valet Parking", "total_slots": 150,  "price_per_hour": 8.00},
]

RESERVATIONS = [
    {"customer_name": "Jan de Vries",      "car_number": "VR295H", "parking_id": 1, "start_time": "2026-05-01 08:00", "end_time": "2026-05-01 18:00"},
    {"customer_name": "Sanne van Dijk",    "car_number": "6XTN30", "parking_id": 2, "start_time": "2026-05-02 09:30", "end_time": "2026-05-02 20:00"},
    {"customer_name": "Pieter Bakker",     "car_number": "6XTN45", "parking_id": 3, "start_time": "2026-05-03 07:45", "end_time": "2026-05-05 14:00"},
    {"customer_name": "Lisa Visser",       "car_number": "47SKLP", "parking_id": 1, "start_time": "2026-05-04 10:00", "end_time": "2026-05-04 19:00"},
    {"customer_name": "Tom Jansen",        "car_number": "6XTN43", "parking_id": 4, "start_time": "2026-05-06 06:30", "end_time": "2026-05-06 15:30"},
    {"customer_name": "Eva van der Meer",  "car_number": "HBR74J", "parking_id": 2, "start_time": "2026-05-07 11:00", "end_time": "2026-05-07 21:00"},
    {"customer_name": "Mark Smit",         "car_number": "6XTN67", "parking_id": 3, "start_time": "2026-05-08 09:00", "end_time": "2026-05-09 12:00"},
    {"customer_name": "Anouk Bos",         "car_number": "6XTN50", "parking_id": 1, "start_time": "2026-05-09 13:00", "end_time": "2026-05-09 20:00"},
    {"customer_name": "Ruben van Leeuwen", "car_number": "6XTN59", "parking_id": 4, "start_time": "2026-05-10 05:30", "end_time": "2026-05-10 14:00"},
    {"customer_name": "Sophie Kramer",     "car_number": "XTN47",  "parking_id": 2, "start_time": "2026-05-10 12:00", "end_time": "2026-05-11 09:00"},
    {"customer_name": "Daan Meijer",       "car_number": "6XTN57", "parking_id": 3, "start_time": "2026-05-11 08:30", "end_time": "2026-05-11 17:30"},
    {"customer_name": "Noor van den Berg", "car_number": "6XTN47", "parking_id": 1, "start_time": "2026-05-12 07:00", "end_time": "2026-05-12 16:00"},
    {"customer_name": "Lars Hoekstra",     "car_number": "47RGBL", "parking_id": 2, "start_time": "2026-05-13 10:00", "end_time": "2026-05-14 11:00"},
    {"customer_name": "Femke Verhoeven",   "car_number": "1ZKJ05", "parking_id": 3, "start_time": "2026-05-14 09:15", "end_time": "2026-05-14 18:00"},
    {"customer_name": "Joris Mulder",      "car_number": "6XTN75", "parking_id": 4, "start_time": "2026-05-15 06:00", "end_time": "2026-05-15 13:00"},
]


def seed_parking_spaces(conn: sqlite3.Connection) -> None:
    """Populate parking_spaces with initial locations."""
    for space in PARKING_SPACES:
        insert_row(conn, "parking_spaces", space)


def seed_reservations(conn: sqlite3.Connection) -> None:
    """Populate reservations with sample entries."""
    for reservation in RESERVATIONS:
        insert_row(conn, "reservations", reservation)
