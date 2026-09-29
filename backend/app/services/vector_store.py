"""Persistent ChromaDB storage for document chunks."""

from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Any, Sequence

import chromadb

from app.core.config import settings
from app.schemas.retrieval import DocumentChunk, RetrievalResult


class VectorStore:
    """Small, lazy wrapper around a persistent Chroma collection."""

    def __init__(
        self,
        persist_dir: str | Path = settings.CHROMA_PERSIST_DIR,
        collection_name: str = settings.CHROMA_COLLECTION_NAME,
        client: Any | None = None,
    ) -> None:
        self.persist_dir = Path(persist_dir)
        self.collection_name = collection_name
        self._client = client
        self._collection: Any | None = None
        self._lock = Lock()
        self.generation = 0

    @property
    def collection(self) -> Any:
        if self._collection is None:
            with self._lock:
                if self._collection is None:
                    if self._client is None:
                        self.persist_dir.mkdir(parents=True, exist_ok=True)
                        self._client = chromadb.PersistentClient(path=str(self.persist_dir))
                    self._collection = self._client.get_or_create_collection(
                        name=self.collection_name,
                        metadata={"hnsw:space": "cosine"},
                    )
        return self._collection

    @staticmethod
    def _where(document_ids: Sequence[str]) -> dict[str, Any]:
        ids = list(dict.fromkeys(document_ids))
        if len(ids) == 1:
            return {"document_id": ids[0]}
        return {"document_id": {"$in": ids}}

    def upsert_chunks(
        self, chunks: Sequence[DocumentChunk], embeddings: Sequence[Sequence[float]]
    ) -> None:
        if not chunks:
            return
        if len(chunks) != len(embeddings):
            raise ValueError("Each chunk must have one embedding")
        self.collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            embeddings=[list(vector) for vector in embeddings],
            metadatas=[
                {
                    "document_id": chunk.document_id,
                    "owner_id": chunk.owner_id,
                    "filename": chunk.filename,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                }
                for chunk in chunks
            ],
        )
        self.generation += 1

    def delete_document(self, document_id: str) -> None:
        self.collection.delete(where={"document_id": document_id})
        self.generation += 1

    def is_indexed(self, document_id: str) -> bool:
        result = self.collection.get(where={"document_id": document_id}, limit=1)
        return bool(result.get("ids"))

    def get_chunks(self, document_ids: Sequence[str]) -> list[DocumentChunk]:
        if not document_ids:
            return []
        result = self.collection.get(
            where=self._where(document_ids), include=["documents", "metadatas"]
        )
        chunks: list[DocumentChunk] = []
        for chunk_id, text, metadata in zip(
            result.get("ids", []),
            result.get("documents", []),
            result.get("metadatas", []),
            strict=True,
        ):
            chunks.append(self._to_chunk(chunk_id, text, metadata))
        return sorted(chunks, key=lambda item: (item.document_id, item.page_number, item.chunk_index))

    def semantic_search(
        self,
        query_embedding: Sequence[float],
        document_ids: Sequence[str],
        top_k: int,
    ) -> list[RetrievalResult]:
        if not document_ids:
            return []
        result = self.collection.query(
            query_embeddings=[list(query_embedding)],
            n_results=top_k,
            where=self._where(document_ids),
            include=["documents", "metadatas", "distances"],
        )
        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        matches: list[RetrievalResult] = []
        for chunk_id, text, metadata, distance in zip(
            ids, documents, metadatas, distances, strict=True
        ):
            similarity = max(0.0, min(1.0, 1.0 - (float(distance) / 2.0)))
            matches.append(
                RetrievalResult(
                    **self._to_chunk(chunk_id, text, metadata).model_dump(),
                    semantic_score=similarity,
                )
            )
        return matches

    @staticmethod
    def _to_chunk(chunk_id: str, text: str, metadata: dict[str, Any]) -> DocumentChunk:
        return DocumentChunk(
            chunk_id=chunk_id,
            document_id=str(metadata["document_id"]),
            owner_id=str(metadata["owner_id"]),
            filename=str(metadata["filename"]),
            page_number=int(metadata["page_number"]),
            chunk_index=int(metadata["chunk_index"]),
            text=text,
        )


vector_store = VectorStore()
