import sqlite3

from ..config import DB_PATH


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Return a SQLite connection with row_factory set to sqlite3.Row."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def insert_row(conn: sqlite3.Connection, table_name: str, data: dict) -> dict:
    """Insert a single row into a table. Used internally for seeding."""
    cursor = conn.cursor()
    columns = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    cursor.execute(
        f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})",
        tuple(data.values()),
    )
    conn.commit()
    return {"status": "success", "inserted_data": data}
