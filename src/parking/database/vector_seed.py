"""
One-time Weaviate seeding — chunks the parking PDF and inserts it into the collection.

Run once (requires Docker running first):
    docker compose up
    python -m parking.database.vector_seed
"""

import os
from pathlib import Path
from typing import List

import joblib
from tqdm import tqdm
from weaviate.util import generate_uuid5
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters.character import RecursiveCharacterTextSplitter

from .vector import get_client, get_or_create_collection

ROOT = Path(__file__).parent.parent.parent.parent  # src/parking/database -> src/parking -> src -> root
DEFAULT_PDF = str(ROOT / "General_Terms_and_Conditions_Schiphol_Parking.pdf")
DEFAULT_JOBLIB = str(ROOT / "parking_static_data.joblib")


def chunk_split_joblib(
    file_paths: List[str],
    joblib_path: str = DEFAULT_JOBLIB,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> list:
    """Load PDF files, split into chunks, and save to a joblib file."""
    all_chunks = []

    for path in file_paths:
        loader = PyPDFLoader(path)
        documents = loader.load()
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
        chunks = splitter.split_documents(documents)
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "title": f"{os.path.basename(path)}_chunk_{i + 1}",
                "content": chunk.page_content,
            })

    joblib.dump(all_chunks, joblib_path)
    print(f"{len(all_chunks)} chunks saved to {joblib_path}")
    return all_chunks


def insert_elements(
    file_paths: List[str],
    collection_name: str = "static_parking_info_collection",
    joblib_path: str = DEFAULT_JOBLIB,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
    force_recreate: bool = False,
) -> None:
    """Chunk PDFs and insert them into a Weaviate collection."""
    data = chunk_split_joblib(file_paths, joblib_path, chunk_size, chunk_overlap)
    collection = get_or_create_collection(collection_name, force_recreate=force_recreate)

    with collection.batch.fixed_size(batch_size=1, concurrent_requests=1) as batch:
        for document in tqdm(data, desc="Inserting documents into Weaviate"):
            uuid = generate_uuid5(f"{document['title']}_{document['content'][:30]}")
            batch.add_object(properties=document, uuid=uuid)


def seed_parking_pdf(path: str = DEFAULT_PDF, force_recreate: bool = False) -> None:
    """Insert the Schiphol parking PDF into Weaviate. Safe to skip if already seeded."""
    client = get_client()
    collection_name = "static_parking_info_collection"

    if not force_recreate and client.collections.exists(collection_name):
        print("Weaviate collection already exists — skipping seed.")
        return

    insert_elements([path], force_recreate=force_recreate)
    print("Weaviate seeding complete.")



