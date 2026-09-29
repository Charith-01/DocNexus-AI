"""Authenticated Document Intelligence processing and result routes."""

from typing import Any, NoReturn

from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.document_intelligence.agent import (
    DocumentAccessDeniedError,
    DocumentAlreadyProcessingError,
    DocumentIntelligenceError,
    DocumentNotFoundError,
    DocumentProcessingFailedError,
    DocumentSourceUnavailableError,
    DocumentTextUnavailableError,
    IntelligenceNotAvailableError,
    InvalidDocumentIdError,
    document_intelligence_agent,
)
from app.auth.dependencies import get_current_user
from app.schemas.intelligence import DocumentIntelligenceResult
from app.services.nlp_service import SpacyModelUnavailableError
from app.services.pdf_processing import PDFProcessingError
from app.services.processed_storage import ProcessedArtifactError


router = APIRouter(prefix="/documents", tags=["Document Intelligence"])


def _raise_http_error(exc: Exception) -> NoReturn:
    if isinstance(exc, (InvalidDocumentIdError, DocumentNotFoundError)):
        raise HTTPException(status_code=404, detail="Document not found") from exc
    if isinstance(exc, DocumentAccessDeniedError):
        raise HTTPException(status_code=403, detail="Document access denied") from exc
    if isinstance(exc, DocumentAlreadyProcessingError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, IntelligenceNotAvailableError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(
        exc,
        (DocumentTextUnavailableError, DocumentSourceUnavailableError, PDFProcessingError),
    ):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if isinstance(exc, SpacyModelUnavailableError):
        raise HTTPException(
            status_code=503,
            detail="Document analysis model is unavailable",
        ) from exc
    if isinstance(exc, (ProcessedArtifactError, DocumentProcessingFailedError)):
        raise HTTPException(status_code=500, detail="Document processing failed") from exc
    if isinstance(exc, DocumentIntelligenceError):
        raise HTTPException(status_code=500, detail="Document processing failed") from exc
    raise HTTPException(status_code=500, detail="Document processing failed") from exc


@router.post("/{document_id}/process", response_model=DocumentIntelligenceResult)
def process_document(
    document_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> DocumentIntelligenceResult:
    """Synchronously process an authorized PDF for this university MVP."""

    try:
        return document_intelligence_agent.process(document_id, current_user["_id"])
    except Exception as exc:
        _raise_http_error(exc)


@router.get("/{document_id}/intelligence", response_model=DocumentIntelligenceResult)
def get_document_intelligence(
    document_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> DocumentIntelligenceResult:
    """Return stored intelligence without exposing processed filesystem paths."""

    try:
        return document_intelligence_agent.get_intelligence(
            document_id,
            current_user["_id"],
        )
    except Exception as exc:
        _raise_http_error(exc)
