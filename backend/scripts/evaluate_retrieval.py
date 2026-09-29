"""Evaluate BM25, semantic, and hybrid retrieval using manually labeled queries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any

from bson import ObjectId

from app.agents.retrieval.agent import information_retrieval_agent
from app.schemas.retrieval import RetrievalMode, RetrievalSearchRequest
from app.services.retrieval_metrics import precision_at_k, recall_at_k, reciprocal_rank


def evaluate(path: Path, user_id: ObjectId, k: int) -> dict[str, dict[str, float]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    queries: list[dict[str, Any]] = payload.get("queries", payload) if isinstance(payload, dict) else payload
    if not queries:
        raise ValueError("Evaluation file has no labeled queries")
    output: dict[str, dict[str, float]] = {}
    for mode in RetrievalMode:
        precision_values: list[float] = []
        recall_values: list[float] = []
        reciprocal_values: list[float] = []
        for item in queries:
            relevant = set(item["relevant_document_ids"])
            response = information_retrieval_agent.search(
                RetrievalSearchRequest(
                    query=item["query"],
                    document_ids=item.get("document_ids", []),
                    mode=mode,
                    top_k=k,
                ),
                user_id,
            )
            retrieved = [result.document_id for result in response.results]
            precision_values.append(precision_at_k(retrieved, relevant, k))
            recall_values.append(recall_at_k(retrieved, relevant, k))
            reciprocal_values.append(reciprocal_rank(retrieved, relevant))
        output[mode.value] = {
            f"precision@{k}": mean(precision_values),
            f"recall@{k}": mean(recall_values),
            "mrr": mean(reciprocal_values),
        }
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query_file", type=Path)
    parser.add_argument("--user-id", required=True, type=ObjectId)
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()
    results = evaluate(args.query_file, args.user_id, args.k)
    print(f"{'Mode':<10} {'Precision':>10} {'Recall':>10} {'MRR':>10}")
    for mode, metrics in results.items():
        print(
            f"{mode:<10} {metrics[f'precision@{args.k}']:>10.4f} "
            f"{metrics[f'recall@{args.k}']:>10.4f} {metrics['mrr']:>10.4f}"
        )


if __name__ == "__main__":
    main()
