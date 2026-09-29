"""Authenticated indexing and Information Retrieval routes."""

from typing import Any, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.agents.retrieval.agent import (
    DocumentAccessDeniedError,
    DocumentAlreadyIndexingError,
    DocumentIndexingError,
    DocumentNotFoundError,
    DocumentNotProcessedError,
    InvalidDocumentIdError,
    RetrievalError,
    information_retrieval_agent,
)
from app.auth.dependencies import get_current_user
from app.schemas.retrieval import (
    IndexResponse,
    IndexStatusResponse,
    RetrievalSearchRequest,
    RetrievalSearchResponse,
)

router = APIRouter(tags=["Information Retrieval"])


def _raise_http_error(exc: Exception) -> NoReturn:
    if isinstance(exc, (InvalidDocumentIdError, DocumentNotFoundError)):
        raise HTTPException(status_code=404, detail="Document not found") from exc
    if isinstance(exc, DocumentAccessDeniedError):
        raise HTTPException(status_code=403, detail="Document access denied") from exc
    if isinstance(exc, (DocumentNotProcessedError, DocumentAlreadyIndexingError)):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, DocumentIndexingError):
        raise HTTPException(status_code=500, detail="Document indexing failed") from exc
    if isinstance(exc, RetrievalError):
        raise HTTPException(status_code=500, detail="Retrieval operation failed") from exc
    raise HTTPException(status_code=500, detail="Retrieval operation failed") from exc


@router.post("/documents/{document_id}/index", response_model=IndexResponse)
def index_document(
    document_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> IndexResponse:
    try:
        return information_retrieval_agent.index_document(document_id, current_user["_id"])
    except Exception as exc:
        _raise_http_error(exc)


@router.delete("/documents/{document_id}/index", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_index(
    document_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> Response:
    try:
        information_retrieval_agent.remove_document_index(document_id, current_user["_id"])
    except Exception as exc:
        _raise_http_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/documents/{document_id}/index-status", response_model=IndexStatusResponse)
def get_document_index_status(
    document_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> IndexStatusResponse:
    try:
        return information_retrieval_agent.get_index_status(document_id, current_user["_id"])
    except Exception as exc:
        _raise_http_error(exc)


@router.post("/retrieval/search", response_model=RetrievalSearchResponse)
def search_documents(
    request: RetrievalSearchRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> RetrievalSearchResponse:
    try:
        return information_retrieval_agent.search(request, current_user["_id"])
    except Exception as exc:
        _raise_http_error(exc)
