"""Authorization-aware orchestration for indexing and ranked retrieval."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from pymongo.collection import Collection

from app.agents.document_intelligence.agent import get_processed_pages
from app.auth.authorization import can_access_document, get_authorized_document_ids
from app.core.config import settings
from app.db.mongodb import documents_collection
from app.schemas.retrieval import (
    IndexResponse,
    IndexStatusResponse,
    RetrievalMode,
    RetrievalResult,
    RetrievalSearchRequest,
    RetrievalSearchResponse,
)
from app.services.bm25 import BM25Retriever
from app.services.chunking import chunk_pages
from app.services.embedding import EmbeddingService
from app.services.hybrid_retrieval import combine_results
from app.services.vector_store import VectorStore, vector_store


class RetrievalError(RuntimeError):
    pass


class InvalidDocumentIdError(RetrievalError):
    pass


class DocumentNotFoundError(RetrievalError):
    pass


class DocumentAccessDeniedError(RetrievalError):
    pass


class DocumentNotProcessedError(RetrievalError):
    pass


class DocumentAlreadyIndexingError(RetrievalError):
    pass


class DocumentIndexingError(RetrievalError):
    pass


class InformationRetrievalAgent:
    """Coordinate retrieval services while enforcing document authorization."""

    def __init__(
        self,
        collection: Collection[dict[str, Any]] = documents_collection,
        store: VectorStore = vector_store,
        embedder: EmbeddingService | None = None,
        page_loader: Callable[[str, ObjectId], list[dict[str, int | str]]] = get_processed_pages,
        access_checker: Callable[[dict[str, Any], ObjectId], bool] = can_access_document,
        authorized_ids_loader: Callable[[ObjectId], list[str]] = get_authorized_document_ids,
    ) -> None:
        self.collection = collection
        self.store = store
        self.embedder = embedder or EmbeddingService()
        self.page_loader = page_loader
        self.access_checker = access_checker
        self.authorized_ids_loader = authorized_ids_loader
        self.bm25 = BM25Retriever(store)

    @staticmethod
    def _object_id(document_id: str) -> ObjectId:
        if not ObjectId.is_valid(document_id):
            raise InvalidDocumentIdError("Invalid document identifier")
        return ObjectId(document_id)

    def _authorized_document(self, document_id: str, user_id: ObjectId) -> dict[str, Any]:
        document = self.collection.find_one({"_id": self._object_id(document_id)})
        if document is None:
            raise DocumentNotFoundError("Document not found")
        if not self.access_checker(document, user_id):
            raise DocumentAccessDeniedError("Document access denied")
        return document

    def index_document(self, document_id: str, user_id: ObjectId) -> IndexResponse:
        document = self._authorized_document(document_id, user_id)
        if document.get("status") != "processed":
            raise DocumentNotProcessedError("Document must be processed before indexing")
        claimed = self.collection.update_one(
            {"_id": document["_id"], "retrieval_status": {"$ne": "indexing"}},
            {
                "$set": {"retrieval_status": "indexing", "updated_at": datetime.now(UTC)},
                "$unset": {"retrieval_error": ""},
            },
        )
        if getattr(claimed, "matched_count", 1) == 0:
            raise DocumentAlreadyIndexingError("Document is already being indexed")
        try:
            pages = self.page_loader(document_id, user_id)
            chunks = chunk_pages(
                pages,
                document_id,
                str(document["owner_id"]),
                document.get("original_filename", "document.pdf"),
                settings.RETRIEVAL_CHUNK_SIZE,
                settings.RETRIEVAL_CHUNK_OVERLAP,
            )
            if not chunks:
                raise DocumentIndexingError("Processed document has no indexable text")
            embeddings = self.embedder.embed_texts([chunk.text for chunk in chunks])
            self.store.delete_document(document_id)
            self.store.upsert_chunks(chunks, embeddings)
            self.bm25.invalidate()
            indexed_at = datetime.now(UTC)
            self.collection.update_one(
                {"_id": document["_id"]},
                {
                    "$set": {
                        "retrieval_status": "indexed",
                        "indexed_at": indexed_at,
                        "indexed_chunk_count": len(chunks),
                        "embedding_model": settings.EMBEDDING_MODEL,
                        "updated_at": indexed_at,
                    },
                    "$unset": {"retrieval_error": ""},
                },
            )
            return IndexResponse(
                document_id=document_id,
                retrieval_status="indexed",
                indexed_chunk_count=len(chunks),
                embedding_model=settings.EMBEDDING_MODEL,
                indexed_at=indexed_at,
            )
        except Exception as exc:
            self.collection.update_one(
                {"_id": document["_id"]},
                {
                    "$set": {
                        "retrieval_status": "index_failed",
                        "retrieval_error": "Document indexing failed",
                        "updated_at": datetime.now(UTC),
                    }
                },
            )
            if isinstance(exc, DocumentIndexingError):
                raise
            raise DocumentIndexingError("Document indexing failed") from exc

    def remove_document_index(self, document_id: str, user_id: ObjectId) -> None:
        document = self._authorized_document(document_id, user_id)
        self.store.delete_document(document_id)
        self.bm25.invalidate()
        self.collection.update_one(
            {"_id": document["_id"]},
            {
                "$set": {"retrieval_status": "not_indexed", "updated_at": datetime.now(UTC)},
                "$unset": {
                    "indexed_at": "",
                    "indexed_chunk_count": "",
                    "embedding_model": "",
                    "retrieval_error": "",
                },
            },
        )

    def cleanup_deleted_document(self, document_id: str) -> None:
        """Remove vectors before its MongoDB authorization record is deleted."""
        self.store.delete_document(document_id)
        self.bm25.invalidate()

    def get_index_status(self, document_id: str, user_id: ObjectId) -> IndexStatusResponse:
        document = self._authorized_document(document_id, user_id)
        return IndexStatusResponse(
            document_id=document_id,
            retrieval_status=document.get("retrieval_status", "not_indexed"),
            indexed_chunk_count=document.get("indexed_chunk_count", 0),
            embedding_model=document.get("embedding_model"),
            indexed_at=document.get("indexed_at"),
        )

    def _indexed_document_ids(
        self, requested_ids: list[str], user_id: ObjectId
    ) -> list[str]:
        if requested_ids:
            authorized = [str(self._authorized_document(item, user_id)["_id"]) for item in requested_ids]
        else:
            authorized = self.authorized_ids_loader(user_id)
        if not authorized:
            return []
        object_ids = [self._object_id(item) for item in authorized]
        indexed = self.collection.find(
            {"_id": {"$in": object_ids}, "retrieval_status": "indexed"}, {"_id": 1}
        )
        return sorted(str(item["_id"]) for item in indexed)

    def search(
        self, request: RetrievalSearchRequest, user_id: ObjectId
    ) -> RetrievalSearchResponse:
        document_ids = self._indexed_document_ids(request.document_ids, user_id)
        results: list[RetrievalResult] = []
        candidate_count = min(100, max(request.top_k, request.top_k * 4))
        if document_ids and request.mode in (RetrievalMode.SEMANTIC, RetrievalMode.HYBRID):
            semantic = self.store.semantic_search(
                self.embedder.embed_query(request.query), document_ids, candidate_count
            )
        else:
            semantic = []
        if document_ids and request.mode in (RetrievalMode.BM25, RetrievalMode.HYBRID):
            bm25 = self.bm25.search(request.query, document_ids, candidate_count)
        else:
            bm25 = []
        if request.mode == RetrievalMode.SEMANTIC:
            results = semantic[: request.top_k]
        elif request.mode == RetrievalMode.BM25:
            results = bm25[: request.top_k]
        else:
            results = combine_results(
                semantic,
                bm25,
                request.top_k,
                settings.HYBRID_SEMANTIC_WEIGHT,
                settings.HYBRID_BM25_WEIGHT,
            )
        return RetrievalSearchResponse(
            query=request.query,
            mode=request.mode,
            result_count=len(results),
            results=results,
        )


information_retrieval_agent = InformationRetrievalAgent()


def retrieve_evidence(
    query: str,
    user_id: ObjectId,
    document_ids: list[str] | None = None,
    top_k: int = settings.RETRIEVAL_TOP_K,
) -> list[dict[str, Any]]:
    """Stable Member 1/Member 4 contract returning ranked evidence only."""
    response = information_retrieval_agent.search(
        RetrievalSearchRequest(
            query=query,
            document_ids=document_ids or [],
            top_k=top_k,
            mode=RetrievalMode.HYBRID,
        ),
        user_id,
    )
    return [
        {
            "document_id": item.document_id,
            "filename": item.filename,
            "page_number": item.page_number,
            "chunk_id": item.chunk_id,
            "text": item.text,
            "score": item.hybrid_score or 0.0,
        }
        for item in response.results
    ]
