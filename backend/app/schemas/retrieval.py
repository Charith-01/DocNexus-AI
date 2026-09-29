"""Contracts for document indexing and ranked retrieval evidence."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class RetrievalMode(StrEnum):
    SEMANTIC = "semantic"
    BM25 = "bm25"
    HYBRID = "hybrid"


class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    owner_id: str
    filename: str
    page_number: int = Field(ge=1)
    chunk_index: int = Field(ge=0)
    text: str


class RetrievalResult(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    chunk_index: int
    text: str
    semantic_score: float | None = None
    bm25_score: float | None = None
    hybrid_score: float | None = None


class RetrievalSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2_000)
    document_ids: list[str] = Field(default_factory=list, max_length=100)
    mode: RetrievalMode = RetrievalMode.HYBRID
    top_k: int = Field(default=5, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Query must not be blank")
        return value


class RetrievalSearchResponse(BaseModel):
    query: str
    mode: RetrievalMode
    result_count: int
    results: list[RetrievalResult]


class IndexResponse(BaseModel):
    document_id: str
    retrieval_status: Literal["indexed"]
    indexed_chunk_count: int
    embedding_model: str
    indexed_at: datetime


class IndexStatusResponse(BaseModel):
    document_id: str
    retrieval_status: Literal[
        "not_indexed", "indexing", "indexed", "index_failed"
    ]
    indexed_chunk_count: int = 0
    embedding_model: str | None = None
    indexed_at: datetime | None = None
