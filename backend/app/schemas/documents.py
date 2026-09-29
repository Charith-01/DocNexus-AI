"""Document API schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    id: str
    owner_id: str
    original_filename: str
    file_size: int
    mime_type: str
    sha256: str
    status: str
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


class UploadResponse(BaseModel):
    message: str = "PDF uploaded successfully"
    document: DocumentResponse


class DocumentPermissionResponse(BaseModel):
    document_id: str
    user_id: str
    role: Literal["owner", "viewer"]


class DocumentIds(BaseModel):
    document_ids: list[str] = Field(default_factory=list)
