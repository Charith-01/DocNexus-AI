"""Weighted fusion of semantic and BM25 retrieval results."""

from __future__ import annotations

from collections.abc import Sequence

from app.schemas.retrieval import RetrievalResult


def _normalize(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    low, high = min(values.values()), max(values.values())
    if high == low:
        return {key: 1.0 for key in values}
    return {key: (value - low) / (high - low) for key, value in values.items()}


def combine_results(
    semantic: Sequence[RetrievalResult],
    bm25: Sequence[RetrievalResult],
    top_k: int,
    semantic_weight: float,
    bm25_weight: float,
) -> list[RetrievalResult]:
    by_id = {result.chunk_id: result for result in [*semantic, *bm25]}
    semantic_raw = {item.chunk_id: float(item.semantic_score or 0) for item in semantic}
    bm25_raw = {item.chunk_id: float(item.bm25_score or 0) for item in bm25}
    semantic_normalized = _normalize(semantic_raw)
    bm25_normalized = _normalize(bm25_raw)

    combined: list[RetrievalResult] = []
    for chunk_id, original in by_id.items():
        score = (
            semantic_weight * semantic_normalized.get(chunk_id, 0.0)
            + bm25_weight * bm25_normalized.get(chunk_id, 0.0)
        )
        combined.append(
            RetrievalResult(
                chunk_id=original.chunk_id,
                document_id=original.document_id,
                filename=original.filename,
                page_number=original.page_number,
                chunk_index=original.chunk_index,
                text=original.text,
                semantic_score=semantic_raw.get(chunk_id),
                bm25_score=bm25_raw.get(chunk_id),
                hybrid_score=score,
            )
        )
    combined.sort(
        key=lambda item: (
            -(item.hybrid_score or 0),
            item.document_id,
            item.page_number,
            item.chunk_index,
        )
    )
    return combined[:top_k]
