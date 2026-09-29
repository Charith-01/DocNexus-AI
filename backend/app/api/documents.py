"""Authenticated document management API routes."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status

from app.auth.authorization import can_access_document
from app.agents.retrieval.agent import information_retrieval_agent
from app.auth.dependencies import get_current_user
from app.db.mongodb import document_permissions_collection, documents_collection
from app.schemas.documents import DocumentListResponse, DocumentResponse, UploadResponse
from app.services.document_storage import (
    FileTooLargeError,
    InvalidPDFError,
    resolve_stored_path,
    store_pdf,
)


router = APIRouter(prefix="/documents", tags=["Documents"])


def _document_response(document: dict[str, Any]) -> DocumentResponse:
    return DocumentResponse(
        id=str(document["_id"]),
        owner_id=str(document["owner_id"]),
        original_filename=document["original_filename"],
        file_size=document["file_size"],
        mime_type=document["mime_type"],
        sha256=document["sha256"],
        status=document["status"],
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


def _object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc


def _accessible_document(document_id: str, user_id: ObjectId) -> dict[str, Any]:
    document = documents_collection.find_one({"_id": _object_id(document_id)})
    if document is None or not can_access_document(document, user_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> UploadResponse:
    """Validate and securely persist an authenticated user's PDF."""

    try:
        stored = await store_pdf(file, str(current_user["_id"]))
    except FileTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except InvalidPDFError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()

    now = datetime.now(UTC)
    document = {
        "owner_id": current_user["_id"],
        "original_filename": stored.original_filename,
        "stored_filename": stored.stored_filename,
        "file_path": stored.relative_path,
        "file_size": stored.file_size,
        "mime_type": stored.mime_type,
        "sha256": stored.sha256,
        "status": "uploaded",
        "retrieval_status": "not_indexed",
        "metadata": {},
        "created_at": now,
        "updated_at": now,
    }
    try:
        result = documents_collection.insert_one(document)
    except Exception:
        stored.absolute_path.unlink(missing_ok=True)
        raise

    document["_id"] = result.inserted_id
    return UploadResponse(document=_document_response(document))


@router.get("", response_model=DocumentListResponse)
def list_documents(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> DocumentListResponse:
    """List documents owned by or shared with the authenticated user."""

    user_id = current_user["_id"]
    shared_ids = [
        item["document_id"]
        for item in document_permissions_collection.find(
            {"user_id": user_id, "role": {"$in": ["owner", "viewer"]}},
            {"document_id": 1},
        )
    ]
    query = {"$or": [{"owner_id": user_id}, {"_id": {"$in": shared_ids}}]}
    documents = [
        _document_response(item)
        for item in documents_collection.find(query).sort("created_at", -1)
    ]
    return DocumentListResponse(documents=documents, total=len(documents))


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> DocumentResponse:
    """Return metadata for an accessible document."""

    return _document_response(_accessible_document(document_id, current_user["_id"]))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> Response:
    """Delete an owned document record and its safely resolved PDF."""

    document = documents_collection.find_one({"_id": _object_id(document_id)})
    if document is None or document.get("owner_id") != current_user["_id"]:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        stored_path = resolve_stored_path(document["file_path"])
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Stored document path is invalid") from exc

    try:
        information_retrieval_agent.cleanup_deleted_document(document_id)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Document index cleanup failed; document was not deleted",
        ) from exc

    documents_collection.delete_one({"_id": document["_id"], "owner_id": current_user["_id"]})
    document_permissions_collection.delete_many({"document_id": document["_id"]})
    Path(stored_path).unlink(missing_ok=True)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
