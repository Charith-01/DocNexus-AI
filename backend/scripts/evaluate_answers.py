"""Calculate grounded-QA metrics from manually labeled recorded results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.answer_metrics import (
    abstention_success_rate,
    answerability_accuracy,
    citation_document_accuracy,
    unsupported_claim_rate,
)


def evaluate(path: Path) -> dict[str, float]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    if not cases:
        raise ValueError("Evaluation file has no completed labeled cases")
    expected = [bool(case["expected_answerable"]) for case in cases]
    predicted = [bool(case["actual_answerable"]) for case in cases]
    citation_scores = [
        citation_document_accuracy(
            set(case.get("actual_source_documents", [])),
            set(case.get("expected_source_documents", [])),
        )
        for case in cases
    ]
    claims = [supported for case in cases for supported in case.get("claim_support", [])]
    return {
        "answerability_accuracy": answerability_accuracy(expected, predicted),
        "abstention_success_rate": abstention_success_rate(expected, predicted),
        "citation_document_accuracy": sum(citation_scores) / len(citation_scores),
        "unsupported_claim_rate": unsupported_claim_rate(claims),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_file", type=Path)
    args = parser.parse_args()
    for metric, value in evaluate(args.case_file).items():
        print(f"{metric}: {value:.4f}")


if __name__ == "__main__":
    main()
