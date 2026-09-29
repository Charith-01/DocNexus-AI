"""Responsible-AI metrics for manually labeled grounded-QA evaluations."""

from __future__ import annotations

from collections.abc import Sequence, Set


def answerability_accuracy(expected: Sequence[bool], predicted: Sequence[bool]) -> float:
    if len(expected) != len(predicted):
        raise ValueError("Expected and predicted values must have equal length")
    if not expected:
        return 0.0
    return sum(left == right for left, right in zip(expected, predicted, strict=True)) / len(expected)


def citation_validity_rate(cited_source_ids: Sequence[str], valid_source_ids: Set[str]) -> float:
    if not cited_source_ids:
        return 1.0
    return sum(source_id in valid_source_ids for source_id in cited_source_ids) / len(cited_source_ids)


def citation_document_accuracy(cited_documents: Set[str], expected_documents: Set[str]) -> float:
    if not expected_documents:
        return 1.0 if not cited_documents else 0.0
    return len(cited_documents.intersection(expected_documents)) / len(expected_documents)


def unsupported_claim_rate(claim_support: Sequence[bool]) -> float:
    if not claim_support:
        return 0.0
    return sum(not supported for supported in claim_support) / len(claim_support)


def abstention_success_rate(expected_answerable: Sequence[bool], predicted_answerable: Sequence[bool]) -> float:
    if len(expected_answerable) != len(predicted_answerable):
        raise ValueError("Expected and predicted values must have equal length")
    unanswerable = [
        predicted
        for expected, predicted in zip(expected_answerable, predicted_answerable, strict=True)
        if not expected
    ]
    if not unanswerable:
        return 0.0
    return sum(not predicted for predicted in unanswerable) / len(unanswerable)
