# weaviate_db.py
# Stores static, unstructured parking data (PDFs, text, etc.) in Weaviate for semantic search
#before start, run this:
#docker compose up

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters.character import RecursiveCharacterTextSplitter
from weaviate.classes.config import Configure, Property, DataType
from weaviate.util import generate_uuid5
from tqdm import tqdm
import joblib
import weaviate
import os
from typing import List

# ----------------------------
# Step 1: Initialize Weaviate client
# ----------------------------
def initialize_client(host: str = "localhost", rest_port: int = 8180, grpc_port: int = 50051):
    """
        Initialize and return a Weaviate client connection.

        Parameters:
            host (str): Host address of the Weaviate instance.
            rest_port (int): REST API port.
            grpc_port (int): gRPC port.

        Returns:
            Client: Connected Weaviate client.
        """
    client2 = weaviate.connect_to_local(host=host, port=rest_port, grpc_port=grpc_port)
    print("Live:", client2.is_live())
    print("Ready:", client2.is_ready())
    return client2

client=initialize_client()
# ----------------------------
# Step 2: Vectorizer config
# ----------------------------
def vectorizer_configuration(name: str = "vector", source_properties: List[str] = None):
    """
        Create vectorizer configuration for text embedding.

        Parameters:
            name (str): Name of the vector.
            source_properties (list): Fields to be vectorized.

        Returns:
            list: Vectorizer configuration.
        """

    if source_properties is None:
        source_properties = ['content']
    vectorizer_config = [Configure.NamedVectors.text2vec_transformers(
        name=name,
        source_properties=source_properties,
        vectorize_collection_name=False,
        inference_url="http://t2v-transformers:8080"
    )]
    return vectorizer_config


# ----------------------------
# Step 3: Create or retrieve collection
# ----------------------------
def collection_query(
                     name: str = 'static_parking_info_collection',
                     source_properties: List[str] = None,
                     force_recreate: bool = True):
    """
        Create or retrieve a Weaviate collection.

        Parameters:
            name (str): Collection name.
            source_properties (list): Properties to store.
            force_recreate (bool): If True, deletes and recreates the collection.

        Returns:
            Collection: Weaviate collection object.
        """
    if source_properties is None:
        source_properties = ['content']
    if force_recreate and client.collections.exists(name):
        client.collections.delete(name)

    if not client.collections.exists(name):
        collection = client.collections.create(
            name=name,
            vectorizer_config=vectorizer_configuration(),
            reranker_config=Configure.Reranker.transformers(),
            properties=[Property(name=c, vectorize_property_name=True, data_type=DataType.TEXT)
                        for c in source_properties]
        )
    else:
        collection = client.collections.get(name)
    return collection


# ----------------------------
# Step 4: Chunk PDF files and save to Joblib
# ----------------------------
def chunk_split_joblib(file_paths: List[str],
                       joblib_path: str = "parking_static_data.joblib",
                       chunk_size: int = 500,
                       chunk_overlap: int = 100):
    """
        Load PDF files, split them into chunks, and save them to a Joblib file.

        Parameters:
            file_paths (list): List of PDF file paths.
            joblib_path (str): Path to save chunked data.
            chunk_size (int): Size of each text chunk.
            chunk_overlap (int): Overlap between chunks.

        Returns:
            list: List of chunked documents.
        """
    all_chunks = []

    for path in file_paths:
        loader = PyPDFLoader(path)
        documents = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size,
                                                  chunk_overlap=chunk_overlap,
                                                  length_function=len)
        chunks = splitter.split_documents(documents)

        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "title": f"{os.path.basename(path)}_chunk_{i+1}",
                "content": chunk.page_content
            })

    joblib.dump(all_chunks, joblib_path)
    print(f"{len(all_chunks)} chunks saved to {joblib_path}")
    return all_chunks


# ----------------------------
# Step 5: Insert chunks into Weaviate collection
# ----------------------------
def insert_elements(
                    file_paths: List[str],
                    collection_name: str = 'static_parking_info_collection',
                    joblib_path: str = "parking_static_data.joblib",
                    chunk_size: int = 500,
                    chunk_overlap: int = 100,
                    force_recreate_collection: bool = True):
    """
        Insert chunked documents into a Weaviate collection.

        Parameters:
            file_paths (list): List of PDF file paths.
            collection_name (str): Name of the collection.
            joblib_path (str): Path to save/load chunked data.
            chunk_size (int): Size of text chunks.
            chunk_overlap (int): Overlap between chunks.
            force_recreate_collection (bool): Whether to recreate the collection.

        Returns:
            Collection: Updated Weaviate collection.
        """

    data = chunk_split_joblib(file_paths, joblib_path, chunk_size, chunk_overlap)
    collection = collection_query(collection_name, force_recreate=force_recreate_collection)

    with collection.batch.fixed_size(batch_size=1, concurrent_requests=1) as batch:
        for document in tqdm(data, desc="Inserting documents into Weaviate"):
            uuid = generate_uuid5(f"{document['title']}_{document['content'][:30]}")
            batch.add_object(properties=document, uuid=uuid)

    return collection

# ----------------------------
# Step 6: Insert chunks into Weaviate collection for one doc
# ----------------------------
def insert_parking_docs_once(path="./General_Terms_and_Conditions_Schiphol_Parking.pdf"):
    """
    Insert a single parking PDF document into Weaviate.

    Parameters:
        path (str): Path to the PDF file.
    """

    insert_elements([
        path
    ])


# ----------------------------
# Step 7: Semantic search
# ----------------------------
def search_collection(query: str,
                      limit: int = 4, collection_name: str = 'static_parking_info_collection',):
    """
        Perform a semantic search in the Weaviate collection.

        Parameters:
            query (str): Search query text.
            limit (int): Number of results to return.
            collection_name (str): Name of the collection.

        Returns:
            list: Search results from Weaviate.
        """
    collection=collection_query(collection_name)
    result = collection.query.near_text(query=query, limit=limit)
    return result

if __name__=="__main__":
    """
       Run initial document insertion and close the Weaviate client.
       """
    insert_parking_docs_once()
    client.close()