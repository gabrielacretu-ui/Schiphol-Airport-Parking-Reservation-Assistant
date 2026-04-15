"""
Initialise the SQLite database — creates tables and seeds initial data if empty.

Run once:
    python scripts/database_seeding.py
"""


from parking.database import get_connection, create_tables

if __name__ == "__main__":
    conn = get_connection()
    create_tables(conn)
    print("SQLite database ready.")
    conn.close()
