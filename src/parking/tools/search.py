# chatbot_main.py
from dotenv import load_dotenv
from langchain_classic.tools import  tool

from ..database import search_collection

load_dotenv()


# ---------------------------------------------------
# Weaviate (RAG) functions

# ---------------------------------------------------
@tool
def search_parking_information_tool(query: str):
    """
    Search for parking information in the Weaviate vector database.

    Steps:
    1. Perform a semantic search using the `search_collection` function.
    2. Retrieve the top 3 results.
    3. Return the content of the results as a single concatenated string.

    Args:
        query (str): The user's natural language question or query.

    Returns:
        str: The concatenated text of the top 3 documents found, or an error message
             if no relevant information is found.
    """

    results = search_collection(query)

    docs = [
        obj.properties["content"]
        for obj in results.objects[:3]
    ]

    if docs:
        return "\n".join(docs)

    return "Sorry, I could not find information about that."

def search_parking_information_tool_eval(query: str, fetch_k: int = 10):
    results = search_collection(query)

    docs = [
        obj.properties["content"]
        for obj in results.objects[:fetch_k]
    ]

    return docs