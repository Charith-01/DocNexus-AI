"""Tests for secure PDF validation and storage."""

import asyncio
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.services.document_storage import (
    InvalidPDFError,
    safe_user_directory,
    store_pdf,
)


USER_ID = "507f1f77bcf86cd799439011"


def upload(filename: str, content: bytes, content_type: str = "application/pdf") -> UploadFile:
    return UploadFile(
        file=BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def test_pdf_extension_and_signature_are_validated(tmp_path: Path) -> None:
    with pytest.raises(InvalidPDFError, match="Only PDF"):
        asyncio.run(store_pdf(upload("notes.txt", b"%PDF-1.7"), USER_ID, tmp_path))

    with pytest.raises(InvalidPDFError, match="not a PDF"):
        asyncio.run(store_pdf(upload("notes.pdf", b"not-a-pdf"), USER_ID, tmp_path))


def test_upload_uses_safe_uuid_path_and_hash(tmp_path: Path) -> None:
    stored = asyncio.run(
        store_pdf(upload("../../Agreement.pdf", b"%PDF-1.7\ncontent"), USER_ID, tmp_path)
    )

    assert stored.original_filename == "Agreement.pdf"
    assert stored.stored_filename != "Agreement.pdf"
    assert stored.stored_filename.endswith(".pdf")
    assert stored.absolute_path.is_relative_to(tmp_path.resolve())
    assert stored.absolute_path.read_bytes().startswith(b"%PDF-")
    assert len(stored.sha256) == 64


def test_user_storage_path_rejects_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Invalid user"):
        safe_user_directory("../../outside", tmp_path)
