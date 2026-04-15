"""
Seed the Weaviate vector database — chunks the parking PDF and inserts it.
Skips automatically if the collection already exists.

Requirements:
    - Docker running:  docker compose up
    - Run once:        python scripts/weaviate_seeding.py
"""


from parking.database import get_client
from parking.database import seed_parking_pdf

if __name__ == "__main__":
    seed_parking_pdf()
    get_client().close()
    print("Weaviate database ready.")
