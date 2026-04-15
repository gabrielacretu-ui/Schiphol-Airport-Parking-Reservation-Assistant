from typing import List

import weaviate
from weaviate.classes.config import Configure, Property, DataType

from ..config import WEAVIATE_URL

COLLECTION_NAME = "static_parking_info_collection"

_client = None


# ----------------------------
# Connection
# ----------------------------
def get_client() -> weaviate.WeaviateClient:
    """Return a cached Weaviate client, connecting on first call."""
    global _client
    if _client is None or not _client.is_connected():
        host, port = WEAVIATE_URL.replace("http://", "").split(":")
        _client = weaviate.connect_to_local(host=host, port=int(port), grpc_port=50051)
    return _client


# ----------------------------
# Vectorizer config (internal)
# ----------------------------
def _vectorizer_configuration(name: str = "vector", source_properties: List[str] = None) -> list:
    if source_properties is None:
        source_properties = ["content"]
    return [Configure.NamedVectors.text2vec_transformers(
        name=name,
        source_properties=source_properties,
        vectorize_collection_name=False,
        inference_url="http://t2v-transformers:8080"
    )]


# ----------------------------
# Collection management
# ----------------------------
def get_or_create_collection(
    name: str = COLLECTION_NAME,
    source_properties: List[str] = None,
    force_recreate: bool = False,
):
    """Get an existing collection or create it if it does not exist."""
    if source_properties is None:
        source_properties = ["content"]

    client = get_client()

    if force_recreate and client.collections.exists(name):
        client.collections.delete(name)

    if not client.collections.exists(name):
        return client.collections.create(
            name=name,
            vectorizer_config=_vectorizer_configuration(),
            reranker_config=Configure.Reranker.transformers(),
            properties=[
                Property(name=p, vectorize_property_name=True, data_type=DataType.TEXT)
                for p in source_properties
            ],
        )

    return client.collections.get(name)


# ----------------------------
# Search
# ----------------------------
def search_collection(query: str, limit: int = 4, collection_name: str = COLLECTION_NAME) -> list:
    """Perform a semantic near-text search in the Weaviate collection."""
    collection = get_or_create_collection(collection_name)
    return collection.query.near_text(query=query, limit=limit)
