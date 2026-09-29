"""Secure local storage helpers for user-uploaded PDFs."""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path, PurePath
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings


PROJECT_DIR = Path(__file__).resolve().parents[3]
UPLOAD_ROOT = PROJECT_DIR / "storage" / "uploads"
PDF_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}
USER_ID_PATTERN = re.compile(r"^[0-9a-f]{24}$")


class InvalidPDFError(ValueError):
    """Raised when an upload is not a valid PDF for this MVP."""


class FileTooLargeError(ValueError):
    """Raised when an upload exceeds the configured size limit."""


@dataclass(frozen=True)
class StoredPDF:
    original_filename: str
    stored_filename: str
    relative_path: str
    absolute_path: Path
    file_size: int
    mime_type: str
    sha256: str


def sanitize_display_filename(filename: str | None) -> str:
    """Remove path and control characters from a display-only filename."""

    basename = PurePath((filename or "document.pdf").replace("\\", "/")).name
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "_", basename).strip(" .")
    return (cleaned or "document.pdf")[:255]


def safe_user_directory(user_id: str, upload_root: Path = UPLOAD_ROOT) -> Path:
    """Build a user directory while preventing path traversal."""

    if USER_ID_PATTERN.fullmatch(user_id) is None:
        raise ValueError("Invalid user identifier")
    root = upload_root.resolve()
    directory = (root / user_id).resolve()
    if not directory.is_relative_to(root):
        raise ValueError("Unsafe upload path")
    return directory


def resolve_stored_path(relative_path: str, upload_root: Path = UPLOAD_ROOT) -> Path:
    """Resolve a database path only when it remains below the upload root."""

    root = upload_root.resolve()
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Unsafe stored path")
    return path


async def store_pdf(
    upload: UploadFile,
    user_id: str,
    upload_root: Path = UPLOAD_ROOT,
) -> StoredPDF:
    """Validate, stream, hash, and store one PDF upload."""

    original_filename = sanitize_display_filename(upload.filename)
    if Path(original_filename).suffix.lower() != ".pdf":
        raise InvalidPDFError("Only PDF files are allowed")
    if upload.content_type not in PDF_CONTENT_TYPES:
        raise InvalidPDFError("The upload content type must be application/pdf")

    user_directory = safe_user_directory(user_id, upload_root)
    user_directory.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid4().hex}.pdf"
    target = user_directory / stored_filename
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    digest = hashlib.sha256()
    total_size = 0
    first_chunk = True

    try:
        with target.open("xb") as output:
            while chunk := await upload.read(1024 * 1024):
                if first_chunk:
                    if not chunk.startswith(b"%PDF-"):
                        raise InvalidPDFError("File content is not a PDF")
                    first_chunk = False
                total_size += len(chunk)
                if total_size > max_bytes:
                    raise FileTooLargeError(
                        f"PDF exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB limit"
                    )
                digest.update(chunk)
                output.write(chunk)
        if total_size == 0:
            raise InvalidPDFError("PDF file is empty")
    except Exception:
        target.unlink(missing_ok=True)
        raise

    relative_path = target.relative_to(upload_root.resolve()).as_posix()
    return StoredPDF(
        original_filename=original_filename,
        stored_filename=stored_filename,
        relative_path=relative_path,
        absolute_path=target,
        file_size=total_size,
        mime_type="application/pdf",
        sha256=digest.hexdigest(),
    )
