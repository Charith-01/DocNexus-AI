"""Coordinator for extraction, NLP analysis, artifacts, and MongoDB state."""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bson import ObjectId
from pymongo.collection import Collection

from app.auth.authorization import can_access_document
from app.db.mongodb import documents_collection
from app.schemas.intelligence import DocumentIntelligenceResult, PDFMetadata
from app.services.document_storage import resolve_stored_path
from app.services.nlp_service import NLPService, SpacyModelUnavailableError
from app.services.pdf_processing import (
    ExtractedPDF,
    PDFProcessingError,
    extract_pdf,
)
from app.services.processed_storage import (
    PROCESSED_ROOT,
    ProcessedArtifactError,
    load_processed_pages,
    write_processed_artifacts,
)


class DocumentIntelligenceError(RuntimeError):
    """Base error safe for translation by the API layer."""


class InvalidDocumentIdError(DocumentIntelligenceError):
    pass


class DocumentNotFoundError(DocumentIntelligenceError):
    pass


class DocumentAccessDeniedError(DocumentIntelligenceError):
    pass


class DocumentAlreadyProcessingError(DocumentIntelligenceError):
    pass


class DocumentSourceUnavailableError(DocumentIntelligenceError):
    pass


class DocumentTextUnavailableError(DocumentIntelligenceError):
    pass


class IntelligenceNotAvailableError(DocumentIntelligenceError):
    pass


class DocumentProcessingFailedError(DocumentIntelligenceError):
    pass


class DocumentIntelligenceAgent:
    """Coordinate Member 2 services without implementing retrieval or RAG."""

    def __init__(
        self,
        collection: Collection[dict[str, Any]] = documents_collection,
        nlp_service: NLPService | None = None,
        pdf_extractor: Callable[[Path], ExtractedPDF] = extract_pdf,
        source_resolver: Callable[[str], Path] = resolve_stored_path,
        processed_root: Path = PROCESSED_ROOT,
    ) -> None:
        self.collection = collection
        self.nlp_service = nlp_service or NLPService()
        self.pdf_extractor = pdf_extractor
        self.source_resolver = source_resolver
        self.processed_root = processed_root

    @staticmethod
    def _object_id(document_id: str) -> ObjectId:
        if not ObjectId.is_valid(document_id):
            raise InvalidDocumentIdError("Invalid document identifier")
        return ObjectId(document_id)

    def _authorized_document(
        self,
        document_id: str,
        user_id: ObjectId,
    ) -> dict[str, Any]:
        document = self.collection.find_one({"_id": self._object_id(document_id)})
        if document is None:
            raise DocumentNotFoundError("Document not found")
        if not can_access_document(document, user_id):
            raise DocumentAccessDeniedError("Document access denied")
        return document

    def process(self, document_id: str, user_id: ObjectId) -> DocumentIntelligenceResult:
        """Process an authorized PDF and persist safe state transitions/results."""

        document = self._authorized_document(document_id, user_id)
        if document.get("status") == "processing":
            raise DocumentAlreadyProcessingError("Document is already processing")

        now = datetime.now(UTC)
        claimed = self.collection.update_one(
            {"_id": document["_id"], "status": {"$ne": "processing"}},
            {
                "$set": {
                    "status": "processing",
                    "retrieval_status": "not_indexed",
                    "updated_at": now,
                },
                "$unset": {
                    "processing_error": "",
                    "indexed_at": "",
                    "indexed_chunk_count": "",
                    "embedding_model": "",
                    "retrieval_error": "",
                },
            },
        )
        if getattr(claimed, "matched_count", 1) == 0:
            raise DocumentAlreadyProcessingError("Document is already processing")

        try:
            source_path = self._source_path(document)
            extracted = self.pdf_extractor(source_path)
            if not extracted.is_text_extractable:
                raise DocumentTextUnavailableError(
                    "The PDF has insufficient extractable text and may require OCR"
                )

            owner_id = str(document["owner_id"])
            artifacts = write_processed_artifacts(
                owner_id,
                document_id,
                extracted,
                self.processed_root,
            )
            analysis = self.nlp_service.analyze(
                pages=extracted.pages,
                text=extracted.text,
                filename=document.get("original_filename", "document.pdf"),
                metadata=extracted.metadata,
            )
            processed_at = datetime.now(UTC)
            result = DocumentIntelligenceResult(
                document_id=document_id,
                document_type=analysis.document_type,
                classification_confidence=analysis.classification_confidence,
                summary=analysis.summary,
                keywords=analysis.keywords,
                entities=analysis.entities,
                pdf_metadata=PDFMetadata.model_validate(extracted.metadata),
                page_count=extracted.page_count,
                word_count=extracted.word_count,
                character_count=extracted.character_count,
                is_text_extractable=extracted.is_text_extractable,
                requires_ocr=extracted.requires_ocr,
                processed_at=processed_at,
            )
            self._store_success(document["_id"], result, artifacts)
            return result
        except Exception as exc:
            safe_message = self._safe_error_message(exc)
            self.collection.update_one(
                {"_id": document["_id"]},
                {
                    "$set": {
                        "status": "failed",
                        "processing_error": safe_message,
                        "updated_at": datetime.now(UTC),
                    }
                },
            )
            if isinstance(
                exc,
                (
                    PDFProcessingError,
                    ProcessedArtifactError,
                    SpacyModelUnavailableError,
                    DocumentIntelligenceError,
                ),
            ):
                raise
            raise DocumentProcessingFailedError("Document processing failed") from exc

    def _source_path(self, document: dict[str, Any]) -> Path:
        try:
            source_path = self.source_resolver(document["file_path"])
        except (KeyError, ValueError) as exc:
            raise DocumentSourceUnavailableError("Document source is unavailable") from exc
        if not source_path.is_file():
            raise DocumentSourceUnavailableError("Document source is unavailable")
        return source_path

    def _store_success(
        self,
        object_id: ObjectId,
        result: DocumentIntelligenceResult,
        artifacts: Any,
    ) -> None:
        result_data = result.model_dump(mode="python")
        result_data.pop("document_id")
        self.collection.update_one(
            {"_id": object_id},
            {
                "$set": {
                    **result_data,
                    "status": "processed",
                    "retrieval_status": "not_indexed",
                    "processed_artifacts": {
                        "text": artifacts.text_path,
                        "pages": artifacts.pages_path,
                    },
                    "updated_at": result.processed_at,
                },
                "$unset": {
                    "processing_error": "",
                    "indexed_at": "",
                    "indexed_chunk_count": "",
                    "embedding_model": "",
                    "retrieval_error": "",
                },
            },
        )

    @staticmethod
    def _safe_error_message(exc: Exception) -> str:
        if isinstance(exc, SpacyModelUnavailableError):
            return str(exc)
        if isinstance(exc, PDFProcessingError):
            return str(exc)
        if isinstance(exc, DocumentTextUnavailableError):
            return str(exc)
        if isinstance(exc, DocumentSourceUnavailableError):
            return str(exc)
        if isinstance(exc, ProcessedArtifactError):
            return "Processed document artifacts could not be written"
        return "Document processing failed"

    def get_intelligence(
        self,
        document_id: str,
        user_id: ObjectId,
    ) -> DocumentIntelligenceResult:
        """Return a previously stored result for an authorized user."""

        document = self._authorized_document(document_id, user_id)
        if document.get("status") != "processed":
            raise IntelligenceNotAvailableError("Document intelligence is not available")
        try:
            return DocumentIntelligenceResult.model_validate(
                {"document_id": document_id, **document}
            )
        except (KeyError, ValueError) as exc:
            raise IntelligenceNotAvailableError(
                "Document intelligence is not available"
            ) from exc

    def get_processed_pages(
        self,
        document_id: str,
        user_id: ObjectId,
    ) -> list[dict[str, int | str]]:
        """Provide authorized page-aware text for Member 3 integration."""

        document = self._authorized_document(document_id, user_id)
        if document.get("status") != "processed":
            raise IntelligenceNotAvailableError("Processed pages are not available")
        return load_processed_pages(
            str(document["owner_id"]),
            document_id,
            self.processed_root,
        )


document_intelligence_agent = DocumentIntelligenceAgent()


def process_document_intelligence(
    document_id: str,
    user_id: ObjectId,
) -> DocumentIntelligenceResult:
    """Stable function for later Member 1 orchestrator execution integration."""

    return document_intelligence_agent.process(document_id, user_id)


def get_processed_pages(
    document_id: str,
    user_id: ObjectId,
) -> list[dict[str, int | str]]:
    """Stable authorized page contract for Member 3 retrieval integration."""

    return document_intelligence_agent.get_processed_pages(document_id, user_id)
