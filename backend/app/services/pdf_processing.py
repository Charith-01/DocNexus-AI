"""Safe, page-aware PDF text and metadata extraction with PyMuPDF."""

import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf


MIN_EXTRACTABLE_CHARACTERS = 20
MIN_EXTRACTABLE_WORDS = 3


class PDFProcessingError(ValueError):
    """Base error for PDFs that cannot be safely processed."""


class CorruptPDFError(PDFProcessingError):
    """Raised when the PDF cannot be parsed."""


class EncryptedPDFError(PDFProcessingError):
    """Raised when the PDF requires a password."""


class EmptyPDFError(PDFProcessingError):
    """Raised when the PDF contains no pages."""


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str


@dataclass(frozen=True)
class ExtractedPDF:
    pages: list[ExtractedPage]
    text: str
    metadata: dict[str, str | None]
    page_count: int
    character_count: int
    word_count: int
    is_text_extractable: bool
    requires_ocr: bool


def normalize_extracted_text(text: str) -> str:
    """Normalize extraction whitespace while preserving paragraph boundaries."""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        lines = [re.sub(r"[\t ]+", " ", line).strip() for line in block.split("\n")]
        normalized = " ".join(line for line in lines if line)
        normalized = re.sub(r" {2,}", " ", normalized).strip()
        if normalized:
            paragraphs.append(normalized)
    return "\n\n".join(paragraphs)


def _metadata(document: pymupdf.Document) -> dict[str, str | None]:
    source = document.metadata or {}
    fields = {
        "title": "title",
        "author": "author",
        "subject": "subject",
        "keywords": "keywords",
        "creator": "creator",
        "producer": "producer",
        "creation_date": "creationDate",
        "modification_date": "modDate",
    }
    return {
        output_name: (source.get(source_name) or None)
        for output_name, source_name in fields.items()
    }


def extract_pdf(pdf_path: Path) -> ExtractedPDF:
    """Extract normalized page text and metadata without performing OCR."""

    try:
        document = pymupdf.open(pdf_path)
    except (pymupdf.FileDataError, RuntimeError, OSError) as exc:
        raise CorruptPDFError("The PDF is corrupt or unreadable") from exc

    try:
        if document.needs_pass or document.is_encrypted:
            raise EncryptedPDFError("Password-protected PDFs are not supported")
        if document.page_count == 0:
            raise EmptyPDFError("The PDF contains no pages")

        pages = [
            ExtractedPage(
                page_number=index + 1,
                text=normalize_extracted_text(page.get_text("text")),
            )
            for index, page in enumerate(document)
        ]
        complete_text = "\n\n".join(page.text for page in pages if page.text)
        word_count = len(re.findall(r"\b\w+\b", complete_text, flags=re.UNICODE))
        character_count = len(complete_text)
        is_text_extractable = (
            character_count >= MIN_EXTRACTABLE_CHARACTERS
            and word_count >= MIN_EXTRACTABLE_WORDS
        )
        return ExtractedPDF(
            pages=pages,
            text=complete_text,
            metadata=_metadata(document),
            page_count=document.page_count,
            character_count=character_count,
            word_count=word_count,
            is_text_extractable=is_text_extractable,
            requires_ocr=not is_text_extractable,
        )
    except PDFProcessingError:
        raise
    except (pymupdf.FileDataError, RuntimeError, ValueError) as exc:
        raise CorruptPDFError("The PDF could not be read safely") from exc
    finally:
        document.close()
