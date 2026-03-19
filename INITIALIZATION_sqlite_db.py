# sqlite_db: stores dynamic, structured data (e.g., availability, working hours, prices).
# Supports keyword search, rapid updates, and established formatting.
import sqlite3


DB_PATH = "dynamic_parking.db"




# ---------------------------------------------------
# Step 1: Connect to SQLite database
# ---------------------------------------------------
def get_sqlite_connection(db_path=r"C:\Users\GabrielaCretu\Desktop\EPAM Onboarding\AI Engineering\Schiphol Airport Parking Reservation Assistant\dynamic_parking.db"):
    """
        Create and return a connection to the SQLite database.

        Parameters:
            db_path (str): Path to the SQLite database file.

        Returns:
            sqlite3.Connection: Connection object with row_factory set to sqlite3.Row.
        """
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection

# ---------------------------------------------------
# Step 2: Initialize database tables
# ---------------------------------------------------
def initialize_db():
    """
        Initialize the SQLite database tables for parking and reservations.

        - Creates 'parking_spaces' table if it doesn't exist.
        - Creates 'reservations' table if it doesn't exist.
        - Populates tables with initial seed data.
        """
    conn=get_sqlite_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS parking_spaces (
            id INTEGER PRIMARY KEY,
            location TEXT NOT NULL UNIQUE,
            total_slots INTEGER NOT NULL,
            price_per_hour REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY,
            customer_name TEXT NOT NULL,
            car_number TEXT NOT NULL,
            parking_id INTEGER NOT NULL,
            start_time DATETIME NOT NULL,
            end_time DATETIME NOT NULL,
            FOREIGN KEY(parking_id) REFERENCES parking_spaces(id),
            UNIQUE(start_time, car_number)
        )
    """)
    seed_parking_data(conn)
    seed_reservations(conn)

    conn.commit()

# ---------------------------------------------------
# Step 3: SQLite simple population function(reservations+parking locations)
# ---------------------------------------------------
def insert_row(conn, table_name, data: dict):
     """
    Insert a row into a specified table.

    Parameters:
        conn (sqlite3.Connection): Database connection.
        table_name (str): Name of the table to insert into.
        data (dict): Dictionary of column names and values to insert.

    Returns:
        dict: Status message including inserted data.
    """

     cursor = conn.cursor()

     columns = ", ".join(data.keys())
     placeholders = ", ".join(["?"] * len(data))

     query = f"""
        INSERT INTO {table_name} ({columns})
        VALUES ({placeholders})
      """

     cursor.execute(query, tuple(data.values()))
     conn.commit()

     return {
        "status": "success",
        "message": f"Row successfully inserted into '{table_name}'.",
        "inserted_data": data
     }
# ---------------------------------------------------
# Step 4: SQLite seed functions(reservations+parking locations)
# ---------------------------------------------------

def seed_parking_data(conn):
    """
    Populate the 'parking_spaces' table with initial parking locations and prices.
    """

    parking_spaces = [
        {
            "location": "Schiphol P1 Short Parking",
            "total_slots": 500,
            "price_per_hour": 6.50
        },
        {
            "location": "Schiphol P3 Long Parking",
            "total_slots": 2000,
            "price_per_hour": 3.00
        },
        {
            "location": "Schiphol P4 Basic Parking",
            "total_slots": 800,
            "price_per_hour": 2.50
        },
        {
            "location": "Schiphol P6 Valet Parking",
            "total_slots": 150,
            "price_per_hour": 8.00
        }
    ]

    for space in parking_spaces:
        insert_row(conn, "parking_spaces", space)
def seed_reservations(conn):
    """
        Populate the 'reservations' table with sample reservation entries.
        """

    reservations = [
        {
            "customer_name": "Jan de Vries",
            "car_number": "VR295H",
            "parking_id": 1,
            "start_time": "2026-04-01 08:00",
            "end_time": "2026-04-01 18:00"
        },
        {
            "customer_name": "Sanne van Dijk",
            "car_number": "6XTN30",
            "parking_id": 2,
            "start_time": "2026-04-02 09:30",
            "end_time": "2026-04-02 20:00"
        },
        {
            "customer_name": "Pieter Bakker",
            "car_number": "6XTN45",
            "parking_id": 3,
            "start_time": "2026-04-03 07:45",
            "end_time": "2026-04-05 14:00"
        },
        {
            "customer_name": "Lisa Visser",
            "car_number": "47SKLP",
            "parking_id": 1,
            "start_time": "2026-04-04 10:00",
            "end_time": "2026-04-04 19:00"
        },
        {
            "customer_name": "Tom Jansen",
            "car_number": "6XTN43",
            "parking_id": 4,
            "start_time": "2026-04-06 06:30",
            "end_time": "2026-04-06 15:30"
        },
        {
            "customer_name": "Eva van der Meer",
            "car_number": "HBR74J",
            "parking_id": 2,
            "start_time": "2026-04-07 11:00",
            "end_time": "2026-04-07 21:00"
        },
        {
            "customer_name": "Mark Smit",
            "car_number": "6XTN67",
            "parking_id": 3,
            "start_time": "2026-04-08 09:00",
            "end_time": "2026-04-09 12:00"
        },
        {
            "customer_name": "Anouk Bos",
            "car_number": "6XTN50",
            "parking_id": 1,
            "start_time": "2026-04-09 13:00",
            "end_time": "2026-04-09 20:00"
        },
        {
            "customer_name": "Ruben van Leeuwen",
            "car_number": "6XTN59",
            "parking_id": 4,
            "start_time": "2026-04-10 05:30",
            "end_time": "2026-04-10 14:00"
        },
        {
            "customer_name": "Sophie Kramer",
            "car_number": "XTN47",
            "parking_id": 2,
            "start_time": "2026-04-10 12:00",
            "end_time": "2026-04-11 09:00"
        },
        {
            "customer_name": "Daan Meijer",
            "car_number": "6XTN57",
            "parking_id": 3,
            "start_time": "2026-04-11 08:30",
            "end_time": "2026-04-11 17:30"
        },
        {
            "customer_name": "Noor van den Berg",
            "car_number": "6XTN47",
            "parking_id": 1,
            "start_time": "2026-04-12 07:00",
            "end_time": "2026-04-12 16:00"
        },
        {
            "customer_name": "Lars Hoekstra",
            "car_number": "47RGBL",
            "parking_id": 2,
            "start_time": "2026-04-13 10:00",
            "end_time": "2026-04-14 11:00"
        },
        {
            "customer_name": "Femke Verhoeven",
            "car_number": "1ZKJ05",
            "parking_id": 3,
            "start_time": "2026-04-14 09:15",
            "end_time": "2026-04-14 18:00"
        },
        {
            "customer_name": "Joris Mulder",
            "car_number": "6XTN75",
            "parking_id": 4,
            "start_time": "2026-04-15 06:00",
            "end_time": "2026-04-15 13:00"
        }
    ]

    for reservation in reservations:
        insert_row(conn, "reservations", reservation)


if __name__=="__main__":
    conn=get_sqlite_connection()
    initialize_db()