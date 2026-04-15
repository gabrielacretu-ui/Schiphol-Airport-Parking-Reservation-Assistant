import json
import time
from typing import List, Dict
from dataclasses import dataclass

from tools.TOOLS_weaviate import search_parking_information_tool_eval


# ---------------------------------------------------
# TEST DATASET (your Schiphol domain)
# ---------------------------------------------------
TEST_CASES = [
    {
        "question": "What is a One-Off Parking Agreement?",
        "expected_keywords": [
            "These Terms and Conditions apply exclusively to One-Off Parking Agreements",
            "car park ticket at the entrance",
            "credit card, with the parking duration being recorded in the PMS",
            "one-off reservation",
            "car park ticket ordered and received in advance"
        ],
        "relevant_section": "Article 3"
    },
    {
        "question": "What is the Excess Fee?",
        "expected_keywords": [
            "€ 100.00 per day",
            "Excess Fee",
            "after 48 hours",
            "P1 Short-Term Parking"
        ],
        "relevant_section": "Article 7"
    },
    {
        "question": "What are the vehicle size limits?",
        "expected_keywords": [
            "5.00 metres",
            "1.90 metres",
            "2,500 kilogrammes",
            "less than two metres in height",
            "maximum height"
        ],
        "relevant_section": "Article 4"
    },
    {
        "question": "How long can I park in the facility?",
        "expected_keywords": [
            "90 consecutive days",
            "Parking Period",
            "entry and exit",
            "time of entry and exit"
        ],
        "relevant_section": "Article 5"
    },
    {
        "question": "What happens if I lose my parking ticket?",
        "expected_keywords": [
            "If the Car Park User loses",
            "Parking Fee for each day",
            "Proof of Parking",
            "present the currently applicable Parking Fee"
        ],
        "relevant_section": "Article 7"
    },
    {
        "question": "Can Schiphol refuse access to the parking facility?",
        "expected_keywords": [
            "refuse access",
            "hazardous substances",
            "reasonableness and fairness",
            "Motor Vehicle may cause damage"
        ],
        "relevant_section": "Article 4"
    },
    {
        "question": "What happens if I exceed reserved parking time?",
        "expected_keywords": [
            "later date/time than the end date/time",
            "charged for the time",
            "€10 per day",
            "€100 per day",
            "Excess Fee"
        ],
        "relevant_section": "Reserved Parking"
    },
    {
        "question": "Is Schiphol liable for damage or theft?",
        "expected_keywords": [
            "excludes any liability",
            "damage, theft, loss",
            "intent or gross negligence",
            "cannot be held liable"
        ],
        "relevant_section": "Article 8"
    },
    {
        "question": "Can I reserve electric charging?",
        "expected_keywords": [
            "not possible to reserve a parking space for Electric Charging",
            "Electric Charging",
            "not guarantee",
            "charging points available"
        ],
        "relevant_section": "Article 3"
    },
    {
        "question": "What law governs the parking agreement?",
        "expected_keywords": [
            "Dutch law",
            "competent court in the district of Amsterdam",
            "governed exclusively",
            "dispute"
        ],
        "relevant_section": "Article 10"
    }
]

# ---------------------------------------------------
# DATA STRUCTURE
# ---------------------------------------------------
@dataclass
class RAGResult:
    question: str
    recall_at_k: float
    precision_at_k: float
    latency_ms: float


# ---------------------------------------------------
# RETRIEVAL WRAPPER
# ---------------------------------------------------
def retrieve(query: str, k: int = 6):
    start = time.time()

    docs = search_parking_information_tool_eval(query, fetch_k=10)

    latency = (time.time() - start) * 1000

    print("\n==============================")
    print(f"QUERY: {query}")
    print("==============================")

    for i, doc in enumerate(docs[:10]):
        print(f"\n[DOC {i}]")
        print(doc[:500])

    return docs[:k], latency


# ---------------------------------------------------
# RECALL@K (keyword-based, adapted to your system)
# ---------------------------------------------------
def compute_recall(retrieved_text: str, expected_keywords: List[str]) -> float:
    if not expected_keywords:
        return 0.0

    hits = sum(
        1 for kw in expected_keywords
        if kw.lower() in retrieved_text.lower()
    )

    return hits / len(expected_keywords)


# ---------------------------------------------------
# PRECISION@K (approximation for your string-based RAG)
# ---------------------------------------------------
def compute_precision(retrieved_text: str, expected_section: str) -> float:
    if not retrieved_text:
        return 0.0

    return 1.0 if expected_section.lower() in retrieved_text.lower() else 0.0


# ---------------------------------------------------
# MAIN EVALUATION LOOP
# ---------------------------------------------------
def evaluate_rag(k: int = 6):
    results = []

    total_recall = 0.0
    total_precision = 0.0
    latencies = []

    for test in TEST_CASES:
        docs, latency = retrieve(test["question"], k=k)

        retrieved_text = " ".join(docs)

        recall = compute_recall(
            retrieved_text,
            test["expected_keywords"]
        )

        precision = compute_precision(
            retrieved_text,
            test["relevant_section"]
        )

        total_recall += recall
        total_precision += precision
        latencies.append(latency)

        results.append(
            RAGResult(
                question=test["question"],
                recall_at_k=recall,
                precision_at_k=precision,
                latency_ms=latency
            ).__dict__
        )

    avg_recall = total_recall / len(TEST_CASES)
    avg_precision = total_precision / len(TEST_CASES)
    avg_latency = sum(latencies) / len(latencies)

    sorted_lat = sorted(latencies)
    p95 = sorted_lat[int(len(sorted_lat) * 0.95) - 1] if sorted_lat else 0

    return {
        "k": k,
        "retrieval": {
            "recall_at_k": avg_recall,
            "precision_at_k": avg_precision,
        },
        "latency": {
            "avg_latency_ms": avg_latency,
            "p95_latency_ms": p95,
        },
        "per_question": results,
    }


# ---------------------------------------------------
# RUN
# ---------------------------------------------------
if __name__ == "__main__":
    report = evaluate_rag(k=6)
    print(json.dumps(report, indent=2))