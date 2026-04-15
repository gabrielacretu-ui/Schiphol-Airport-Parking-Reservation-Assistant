from .connection import get_connection, insert_row
from .schema import create_tables
from .vector import get_client, search_collection
from .vector_seed import seed_parking_pdf

__all__ = [
    "get_connection",
    "create_tables",
    "get_client",
    "search_collection",
    "seed_parking_pdf"
]

# Weaviate imports are intentionally NOT included here.
# Import them explicitly where needed to avoid loading
# Weaviate/LangChain when only SQLite is used:

