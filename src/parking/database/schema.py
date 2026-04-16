import sqlite3

from .seed import seed_parking_spaces, seed_reservations


def create_tables(conn: sqlite3.Connection) -> None:
    """Create tables if they do not exist, then seed if empty."""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS parking_spaces (
            id              INTEGER PRIMARY KEY,
            location        TEXT    NOT NULL UNIQUE,
            total_slots     INTEGER NOT NULL,
            price_per_hour  REAL    NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id            INTEGER  PRIMARY KEY,
            customer_name TEXT     NOT NULL,
            car_number    TEXT     NOT NULL,
            parking_id    INTEGER  NOT NULL,
            start_time    DATETIME NOT NULL,
            end_time      DATETIME NOT NULL,
            FOREIGN KEY (parking_id) REFERENCES parking_spaces(id),
            UNIQUE (start_time, car_number)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_approvals (
            token       TEXT PRIMARY KEY,
            data        TEXT NOT NULL,
            decision    TEXT DEFAULT NULL,
            created_at  TEXT NOT NULL
        )
    """)

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM parking_spaces")
    if cursor.fetchone()[0] == 0:
        seed_parking_spaces(conn)
        seed_reservations(conn)
