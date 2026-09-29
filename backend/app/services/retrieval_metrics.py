"""Standard, API-independent information retrieval evaluation metrics."""

from __future__ import annotations

from collections.abc import Hashable, Sequence


def precision_at_k(
    retrieved: Sequence[Hashable], relevant: set[Hashable], k: int
) -> float:
    """Return relevant items in the first k results divided by k."""
    if k <= 0:
        raise ValueError("k must be positive")
    return sum(item in relevant for item in retrieved[:k]) / k


def recall_at_k(
    retrieved: Sequence[Hashable], relevant: set[Hashable], k: int
) -> float:
    """Return the fraction of all relevant items found in the first k results."""
    if k <= 0:
        raise ValueError("k must be positive")
    if not relevant:
        return 0.0
    return sum(item in relevant for item in set(retrieved[:k])) / len(relevant)


def reciprocal_rank(retrieved: Sequence[Hashable], relevant: set[Hashable]) -> float:
    """Return reciprocal rank of the first relevant result, or zero."""
    for rank, item in enumerate(retrieved, start=1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


def hit_rate_at_k(
    retrieved: Sequence[Hashable], relevant: set[Hashable], k: int
) -> float:
    """Return one when at least one relevant item appears in the first k results."""
    if k <= 0:
        raise ValueError("k must be positive")
    return float(any(item in relevant for item in retrieved[:k]))
