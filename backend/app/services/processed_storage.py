"""Safe persistence and loading of processed page-aware document artifacts."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.services.pdf_processing import ExtractedPDF


PROJECT_DIR = Path(__file__).resolve().parents[3]
PROCESSED_ROOT = PROJECT_DIR / "storage" / "processed"
OBJECT_ID_PATTERN = re.compile(r"^[0-9a-f]{24}$")


class ProcessedArtifactError(ValueError):
    """Raised when processed artifact paths or contents are unsafe."""


@dataclass(frozen=True)
class ProcessedArtifacts:
    text_path: str
    pages_path: str


def _validate_internal_id(value: str, label: str) -> None:
    if OBJECT_ID_PATTERN.fullmatch(value) is None:
        raise ProcessedArtifactError(f"Invalid {label}")


def safe_processed_directory(
    user_id: str,
    document_id: str,
    processed_root: Path = PROCESSED_ROOT,
) -> Path:
    """Return a trusted per-user, per-document directory below processed root."""

    _validate_internal_id(user_id, "user identifier")
    _validate_internal_id(document_id, "document identifier")
    root = processed_root.resolve()
    directory = (root / user_id / document_id).resolve()
    if not directory.is_relative_to(root):
        raise ProcessedArtifactError("Unsafe processed artifact path")
    return directory


def _atomic_write(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(content, encoding="utf-8", newline="\n")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def write_processed_artifacts(
    user_id: str,
    document_id: str,
    extracted: ExtractedPDF,
    processed_root: Path = PROCESSED_ROOT,
) -> ProcessedArtifacts:
    """Atomically write normalized document text and page-aware JSON."""

    directory = safe_processed_directory(user_id, document_id, processed_root)
    directory.mkdir(parents=True, exist_ok=True)
    text_path = directory / "document.txt"
    pages_path = directory / "pages.json"
    payload = {
        "document_id": document_id,
        "pages": [
            {"page_number": page.page_number, "text": page.text}
            for page in extracted.pages
        ],
    }
    _atomic_write(text_path, extracted.text)
    _atomic_write(
        pages_path,
        json.dumps(payload, ensure_ascii=False, indent=2),
    )

    root = processed_root.resolve()
    return ProcessedArtifacts(
        text_path=text_path.relative_to(root).as_posix(),
        pages_path=pages_path.relative_to(root).as_posix(),
    )


def load_processed_pages(
    user_id: str,
    document_id: str,
    processed_root: Path = PROCESSED_ROOT,
) -> list[dict[str, int | str]]:
    """Load and validate page-aware text for later retrieval integration."""

    directory = safe_processed_directory(user_id, document_id, processed_root)
    pages_path = directory / "pages.json"
    try:
        payload = json.loads(pages_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProcessedArtifactError("Processed pages are unavailable") from exc

    if payload.get("document_id") != document_id or not isinstance(payload.get("pages"), list):
        raise ProcessedArtifactError("Processed pages are invalid")

    pages: list[dict[str, int | str]] = []
    for item in payload["pages"]:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("page_number"), int)
            or item["page_number"] < 1
            or not isinstance(item.get("text"), str)
        ):
            raise ProcessedArtifactError("Processed pages are invalid")
        pages.append({"page_number": item["page_number"], "text": item["text"]})
    return pages
