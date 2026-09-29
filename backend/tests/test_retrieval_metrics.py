import pytest

from app.services.retrieval_metrics import (
    hit_rate_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


def test_standard_retrieval_metrics():
    retrieved = ["irrelevant", "relevant", "also-relevant"]
    relevant = {"relevant", "also-relevant", "missing"}
    assert precision_at_k(retrieved, relevant, 2) == 0.5
    assert recall_at_k(retrieved, relevant, 2) == pytest.approx(1 / 3)
    assert reciprocal_rank(retrieved, relevant) == 0.5
    assert hit_rate_at_k(retrieved, relevant, 1) == 0
    assert recall_at_k(retrieved, set(), 5) == 0
