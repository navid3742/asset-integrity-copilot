"""Keyword (BM25) retrieval evaluation on hand-labelled questions.

This only measures the offline retriever. It says nothing about the live agent's
tool choices or answer quality, and the questions were written by someone who
had read the documents, so treat the numbers as a regression check.

Run: PYTHONPATH=backend python backend/scripts/evaluate_retrieval.py
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from app import retrieval

QUERIES = [
    ("P-204 elevated vibration and seal leak history", ["CASE-INC-007", "SOP-PMP-001"]),
    ("pump P-204 incident INC-007 maintenance evidence", ["CASE-INC-007"]),
    ("centrifugal pump vibration trend investigation", ["SOP-PMP-001"]),
    ("what to record when a mechanical seal leaks", ["SOP-PMP-001"]),
    ("pump bearing preventive maintenance work orders", ["SOP-PMP-002"]),
    ("rotating equipment lubrication maintenance history", ["SOP-PMP-002"]),
    ("compare pump condition monitoring readings", ["SOP-PMP-001", "SOP-PMP-002"]),
    ("CV-310 actuator position lag and feedback", ["CASE-INC-010", "SOP-VLV-003"]),
    ("control valve CV-310 incident INC-010", ["CASE-INC-010"]),
    ("positioner calibration and actuator travel deviation", ["SOP-VLV-003"]),
    ("control valve response delay investigation", ["SOP-VLV-003"]),
    ("valve leakage and maintenance handoff", ["SOP-VLV-004"]),
    ("valve packing leakage observation documentation", ["SOP-VLV-004"]),
    ("instrument air and positioner record review", ["SOP-VLV-003"]),
    ("PV-120 UT thickness corrosion trend", ["CASE-INC-012", "SOP-PV-005"]),
    ("pressure vessel PV-120 incident INC-012", ["CASE-INC-012"]),
    ("ultrasonic thickness monitoring vessel wall", ["SOP-PV-005"]),
    ("how to document thickness monitoring location", ["SOP-PV-005"]),
    ("external vessel coating damage corrosion", ["SOP-PV-006"]),
    ("external corrosion vessel supports walkdown", ["SOP-PV-006"]),
    ("how is remaining life assessed with missing design data", ["SOP-PV-005", "SOP-PV-006"]),
    ("mechanical integrity nonconformance review hold", ["SOP-MI-007"]),
    ("corrective action and repair release authorization", ["SOP-MI-007"]),
    ("what are limits for AI engineering disposition", ["POL-AI-010", "SOP-MI-007"]),
    ("permit to work isolation requirements", ["SOP-PTW-008"]),
    ("lockout tagout unauthorized pump restart", ["SOP-PTW-008"]),
    ("safe handoff for energized maintenance", ["SOP-PTW-008"]),
    ("equipment tag traceability inspection record lineage", ["SOP-DATA-009"]),
    ("link inspection IDs to work orders and incidents", ["SOP-DATA-009", "SOP-MI-007"]),
    ("record inspector date measurement unit evidence", ["SOP-DATA-009", "SOP-PV-005"]),
    ("can agent change valve setpoints or approve permits", ["POL-AI-010"]),
    ("prompt injection embedded instructions in documents", ["POL-AI-010", "GUIDE-SEC-015"]),
    ("how to test adversarial tool access controls", ["GUIDE-SEC-015"]),
    ("what tools can the agent call", ["GUIDE-SEC-015", "POL-AI-010"]),
    ("operator quickstart asking questions with asset tags", ["GUIDE-OPS-014"]),
    ("how to read cited source ids and verify evidence", ["GUIDE-OPS-014"]),
]
NEGATIVES = [
    "deep sea plankton aquarium",
    "Who won the world cup?",
    "How much is the CEO salary?",
    "quantum burrito supernova",
    "Explain medieval poetry analysis",
    # Near misses: off-topic questions that share one word with the corpus.
    # The first version of the retriever returned results for all of these.
    "what is the best pizza in town for a pump party",
    "who won the world cup in valve",
    "How much is the CEO salary for pressure",
    "write a poem about valves",
    "tell me a joke",
]


def evaluate():
    rows = []
    first = 0
    third = 0
    mrr = 0
    for query, expected in QUERIES:
        result = retrieval.search(query, top_k=3, semantic=False)
        got = [x["doc_id"] for x in result]
        ranks = [i + 1 for i, x in enumerate(got) if x in expected]
        r = 1 / min(ranks) if ranks else 0
        mrr += r
        first += bool(ranks and min(ranks) == 1)
        third += bool(ranks)
        rows.append({"query": query, "expected": expected, "returned": got, "reciprocal_rank": r})
    negative = []
    for query in NEGATIVES:
        got = [x["doc_id"] for x in retrieval.search(query, top_k=3, semantic=False)]
        negative.append({"query": query, "returned": got, "rejected": not got})
    n = len(QUERIES)
    return {
        "evaluation_type": "OFFLINE keyword (BM25) retrieval only",
        "dataset": "15 fictional oil-and-gas SOP/case documents, 36 hand-labelled questions, 10 unrelated questions (5 share a word with the corpus)",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "total_queries": n,
        "hit_at_1": round(first / n, 4),
        "hit_at_3": round(third / n, 4),
        "mean_reciprocal_rank_at_3": round(mrr / n, 4),
        "unrelated_queries_rejected": sum(row["rejected"] for row in negative),
        "total_unrelated_queries": len(negative),
        "cases": rows,
        "negative_cases": negative,
    }


if __name__ == "__main__":
    data = evaluate()
    path = Path(__file__).resolve().parents[2] / "docs" / "RETRIEVAL_RESULTS.json"
    path.write_text(json.dumps(data, indent=2) + "\n")
    print(
        f"Hit@1: {data['hit_at_1']:.1%}; Hit@3: {data['hit_at_3']:.1%}; MRR@3: {data['mean_reciprocal_rank_at_3']:.3f}; "
        f"unrelated: {data['unrelated_queries_rejected']}/{data['total_unrelated_queries']}"
    )
    print("Saved to docs/RETRIEVAL_RESULTS.json")
    for row in data["cases"]:
        if row["reciprocal_rank"] == 0:
            print("MISSED:", row["query"], "expected", row["expected"], "received", row["returned"])
