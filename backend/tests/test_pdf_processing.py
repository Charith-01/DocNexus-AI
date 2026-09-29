"""Unit tests for safe, page-aware PyMuPDF extraction."""

from pathlib import Path

import pymupdf
import pytest

from app.services.pdf_processing import (
    CorruptPDFError,
    EncryptedPDFError,
    extract_pdf,
    normalize_extracted_text,
)


def create_pdf(path: Path, pages: list[str], metadata: dict[str, str] | None = None) -> None:
    document = pymupdf.open()
    for text in pages:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    if metadata:
        document.set_metadata(metadata)
    document.save(path)
    document.close()


def test_extracts_page_text_metadata_and_counts(tmp_path: Path) -> None:
    path = tmp_path / "report.pdf"
    create_pdf(
        path,
        [
            "First page contains useful project information.",
            "Second page contains final recommendations.",
        ],
        {"title": "Project Report", "author": "DocNexus Team", "subject": "Testing"},
    )

    result = extract_pdf(path)

    assert result.page_count == 2
    assert [page.page_number for page in result.pages] == [1, 2]
    assert result.pages[0].text.startswith("First page")
    assert result.metadata["title"] == "Project Report"
    assert result.metadata["author"] == "DocNexus Team"
    assert result.word_count > 5
    assert result.character_count == len(result.text)
    assert result.is_text_extractable is True
    assert result.requires_ocr is False


def test_blank_pdf_is_flagged_as_non_extractable(tmp_path: Path) -> None:
    path = tmp_path / "blank.pdf"
    create_pdf(path, [""])

    result = extract_pdf(path)

    assert result.text == ""
    assert result.is_text_extractable is False
    assert result.requires_ocr is True


def test_corrupt_and_encrypted_pdfs_fail_safely(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.pdf"
    corrupt.write_bytes(b"%PDF-this-is-not-valid")
    with pytest.raises(CorruptPDFError, match="corrupt or unreadable"):
        extract_pdf(corrupt)

    encrypted = tmp_path / "encrypted.pdf"
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), "Protected document text")
    document.save(
        encrypted,
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="owner-password",
        user_pw="user-password",
    )
    document.close()
    with pytest.raises(EncryptedPDFError, match="Password-protected"):
        extract_pdf(encrypted)


def test_text_normalization_preserves_paragraphs() -> None:
    raw = "First   line\r\ncontinues here.\r\n\r\n  Second\tparagraph.  "

    assert normalize_extracted_text(raw) == (
        "First line continues here.\n\nSecond paragraph."
    )
