"""Tests for safe processed artifact persistence and loading."""

from pathlib import Path

import pytest

from app.services.pdf_processing import ExtractedPDF, ExtractedPage
from app.services.processed_storage import (
    ProcessedArtifactError,
    load_processed_pages,
    safe_processed_directory,
    write_processed_artifacts,
)


USER_ID = "507f1f77bcf86cd799439011"
DOCUMENT_ID = "507f191e810c19729de860ea"


def extracted_document() -> ExtractedPDF:
    pages = [
        ExtractedPage(page_number=1, text="First page text."),
        ExtractedPage(page_number=2, text="Second page text."),
    ]
    return ExtractedPDF(
        pages=pages,
        text="First page text.\n\nSecond page text.",
        metadata={},
        page_count=2,
        character_count=39,
        word_count=6,
        is_text_extractable=True,
        requires_ocr=False,
    )


def test_processed_artifacts_round_trip(tmp_path: Path) -> None:
    artifacts = write_processed_artifacts(
        USER_ID,
        DOCUMENT_ID,
        extracted_document(),
        tmp_path,
    )

    assert artifacts.text_path == f"{USER_ID}/{DOCUMENT_ID}/document.txt"
    assert artifacts.pages_path == f"{USER_ID}/{DOCUMENT_ID}/pages.json"
    assert load_processed_pages(USER_ID, DOCUMENT_ID, tmp_path) == [
        {"page_number": 1, "text": "First page text."},
        {"page_number": 2, "text": "Second page text."},
    ]


def test_processed_path_rejects_external_identifiers(tmp_path: Path) -> None:
    with pytest.raises(ProcessedArtifactError, match="Invalid user"):
        safe_processed_directory("../../outside", DOCUMENT_ID, tmp_path)

    with pytest.raises(ProcessedArtifactError, match="Invalid document"):
        safe_processed_directory(USER_ID, "../document", tmp_path)
