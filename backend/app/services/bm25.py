"""BM25 keyword retrieval over authorized Chroma chunks."""

from __future__ import annotations

import re
from collections.abc import Sequence

from rank_bm25 import BM25Okapi

from app.schemas.retrieval import DocumentChunk, RetrievalResult
from app.services.vector_store import VectorStore

TOKEN_PATTERN = re.compile(r"[\w]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.casefold())


class BM25Retriever:
    def __init__(self, store: VectorStore) -> None:
        self.store = store
        self._cache_key: tuple[tuple[str, ...], int] | None = None
        self._chunks: list[DocumentChunk] = []
        self._index: BM25Okapi | None = None

    def invalidate(self) -> None:
        self._cache_key = None
        self._chunks = []
        self._index = None

    def _load(self, document_ids: Sequence[str]) -> None:
        key = (tuple(sorted(set(document_ids))), self.store.generation)
        if key == self._cache_key:
            return
        self._chunks = self.store.get_chunks(key[0])
        tokenized = [tokenize(chunk.text) for chunk in self._chunks]
        self._index = BM25Okapi(tokenized) if tokenized else None
        self._cache_key = key

    def search(
        self, query: str, document_ids: Sequence[str], top_k: int
    ) -> list[RetrievalResult]:
        query_tokens = tokenize(query)
        if not query_tokens or not document_ids:
            return []
        self._load(document_ids)
        if self._index is None:
            return []
        scores = self._index.get_scores(query_tokens)
        ranked = sorted(
            (
                (chunk, score)
                for chunk, score in zip(self._chunks, scores, strict=True)
                if set(query_tokens).intersection(tokenize(chunk.text))
            ),
            key=lambda pair: (-float(pair[1]), pair[0].document_id, pair[0].page_number, pair[0].chunk_index),
        )
        return [
            RetrievalResult(**chunk.model_dump(), bm25_score=float(score))
            for chunk, score in ranked[:top_k]
        ]
