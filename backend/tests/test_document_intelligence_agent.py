"""Tests for agent coordination and MongoDB processing state transitions."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bson import ObjectId
import pytest

from app.agents.document_intelligence.agent import (
    DocumentAlreadyProcessingError,
    DocumentIntelligenceAgent,
    DocumentTextUnavailableError,
)
from app.schemas.intelligence import EntityGroups, NLPAnalysis
from app.services.pdf_processing import CorruptPDFError, ExtractedPDF, ExtractedPage


USER_ID = ObjectId("507f1f77bcf86cd799439011")
DOCUMENT_ID = ObjectId("507f191e810c19729de860ea")


class UpdateResult:
    def __init__(self, matched_count: int = 1) -> None:
        self.matched_count = matched_count


class FakeDocuments:
    def __init__(self) -> None:
        self.document: dict[str, Any] = {
            "_id": DOCUMENT_ID,
            "owner_id": USER_ID,
            "original_filename": "project-report.pdf",
            "file_path": f"{USER_ID}/stored.pdf",
            "status": "uploaded",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        self.statuses: list[str] = []

    def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        return self.document if query.get("_id") == DOCUMENT_ID else None

    def update_one(self, query: dict[str, Any], update: dict[str, Any]) -> UpdateResult:
        condition = query.get("status")
        if isinstance(condition, dict) and self.document["status"] == condition.get("$ne"):
            return UpdateResult(0)
        for key, value in update.get("$set", {}).items():
            self.document[key] = value
        for key in update.get("$unset", {}):
            self.document.pop(key, None)
        if "status" in update.get("$set", {}):
            self.statuses.append(update["$set"]["status"])
        return UpdateResult()


class StubNLPService:
    @staticmethod
    def analyze(**_: Any) -> NLPAnalysis:
        return NLPAnalysis(
            document_type="Report",
            classification_confidence=0.8,
            summary="This project report contains verified extracted information.",
            keywords=["project report", "information"],
            entities=EntityGroups(),
        )


def extracted_pdf() -> ExtractedPDF:
    text = "This project report contains verified extracted information."
    return ExtractedPDF(
        pages=[ExtractedPage(1, text)],
        text=text,
        metadata={"title": "Project Report"},
        page_count=1,
        character_count=len(text),
        word_count=8,
        is_text_extractable=True,
        requires_ocr=False,
    )


def test_successful_processing_updates_status_and_persists_pages(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-test")
    collection = FakeDocuments()
    agent = DocumentIntelligenceAgent(
        collection=collection,  # type: ignore[arg-type]
        nlp_service=StubNLPService(),  # type: ignore[arg-type]
        pdf_extractor=lambda _: extracted_pdf(),
        source_resolver=lambda _: source,
        processed_root=tmp_path / "processed",
    )

    result = agent.process(str(DOCUMENT_ID), USER_ID)

    assert collection.statuses == ["processing", "processed"]
    assert collection.document["status"] == "processed"
    assert collection.document["document_type"] == "Report"
    assert collection.document["processed_artifacts"]["pages"].endswith("pages.json")
    assert result.status == "processed"
    assert agent.get_processed_pages(str(DOCUMENT_ID), USER_ID)[0]["page_number"] == 1


def test_processing_failure_sets_safe_failed_status(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-test")
    collection = FakeDocuments()

    def fail(_: Path) -> ExtractedPDF:
        raise CorruptPDFError("The PDF is corrupt or unreadable")

    agent = DocumentIntelligenceAgent(
        collection=collection,  # type: ignore[arg-type]
        nlp_service=StubNLPService(),  # type: ignore[arg-type]
        pdf_extractor=fail,
        source_resolver=lambda _: source,
        processed_root=tmp_path / "processed",
    )

    with pytest.raises(CorruptPDFError):
        agent.process(str(DOCUMENT_ID), USER_ID)

    assert collection.statuses == ["processing", "failed"]
    assert collection.document["processing_error"] == "The PDF is corrupt or unreadable"
    assert "Traceback" not in collection.document["processing_error"]


def test_non_text_pdf_sets_failed_status_and_requires_ocr(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-test")
    collection = FakeDocuments()
    blank = ExtractedPDF(
        pages=[ExtractedPage(1, "")],
        text="",
        metadata={},
        page_count=1,
        character_count=0,
        word_count=0,
        is_text_extractable=False,
        requires_ocr=True,
    )
    agent = DocumentIntelligenceAgent(
        collection=collection,  # type: ignore[arg-type]
        nlp_service=StubNLPService(),  # type: ignore[arg-type]
        pdf_extractor=lambda _: blank,
        source_resolver=lambda _: source,
        processed_root=tmp_path / "processed",
    )

    with pytest.raises(DocumentTextUnavailableError, match="require OCR"):
        agent.process(str(DOCUMENT_ID), USER_ID)

    assert collection.document["status"] == "failed"
    assert "OCR" in collection.document["processing_error"]


def test_document_cannot_be_processed_twice_concurrently(tmp_path: Path) -> None:
    collection = FakeDocuments()
    collection.document["status"] = "processing"
    agent = DocumentIntelligenceAgent(
        collection=collection,  # type: ignore[arg-type]
        nlp_service=StubNLPService(),  # type: ignore[arg-type]
        processed_root=tmp_path,
    )

    with pytest.raises(DocumentAlreadyProcessingError):
        agent.process(str(DOCUMENT_ID), USER_ID)

    assert collection.statuses == []


def test_intelligence_result_serialization_excludes_paths(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-test")
    collection = FakeDocuments()
    agent = DocumentIntelligenceAgent(
        collection=collection,  # type: ignore[arg-type]
        nlp_service=StubNLPService(),  # type: ignore[arg-type]
        pdf_extractor=lambda _: extracted_pdf(),
        source_resolver=lambda _: source,
        processed_root=tmp_path / "processed",
    )
    agent.process(str(DOCUMENT_ID), USER_ID)

    payload = agent.get_intelligence(str(DOCUMENT_ID), USER_ID).model_dump(mode="json")

    assert payload["document_id"] == str(DOCUMENT_ID)
    assert "processed_artifacts" not in payload
    assert "file_path" not in payload
