"""Unit tests for explainable spaCy document analysis."""

import spacy
import pytest

from app.services import nlp_service
from app.services.nlp_service import NLPService, SpacyModelUnavailableError
from app.services.pdf_processing import ExtractedPage


def build_test_nlp_service() -> NLPService:
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")
    ruler = nlp.add_pipe("entity_ruler")
    ruler.add_patterns(
        [
            {"label": "ORG", "pattern": "Example Corporation"},
            {"label": "PERSON", "pattern": "Alice Johnson"},
            {"label": "MONEY", "pattern": "$5 million"},
        ]
    )
    return NLPService(nlp)


def test_missing_model_error_contains_setup_command(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_model(_: str) -> None:
        raise OSError("model missing")

    monkeypatch.setattr(nlp_service.spacy, "load", missing_model)

    with pytest.raises(SpacyModelUnavailableError, match="spacy download en_core_web_sm"):
        nlp_service.load_english_model()


def test_entities_are_deduplicated_with_first_page_reference() -> None:
    service = build_test_nlp_service()
    pages = [
        ExtractedPage(1, "Alice Johnson works for Example Corporation."),
        ExtractedPage(2, "Example Corporation invested $5 million."),
    ]

    entities = service.extract_entities(pages)

    assert [(item.text, item.page) for item in entities.organizations] == [
        ("Example Corporation", 1)
    ]
    assert entities.people[0].text == "Alice Johnson"
    assert entities.money[0].page == 2


def test_keywords_are_bounded_and_explainable() -> None:
    service = build_test_nlp_service()
    text = (
        "Renewable energy systems improve energy resilience. "
        "Energy storage supports renewable energy integration and resilient systems."
    )

    keywords = service.extract_keywords(text, limit=5)

    assert 1 <= len(keywords) <= 5
    assert any("energy" in keyword for keyword in keywords)


def test_extractive_summary_uses_original_sentences_in_order() -> None:
    service = build_test_nlp_service()
    sentences = [
        "The research team evaluated renewable energy systems across multiple university buildings.",
        "The weather remained pleasant during the unrelated social event on campus.",
        "Renewable energy generation reduced electricity costs during the twelve month study period.",
        "The analysis found that energy storage improved reliability during periods of peak demand.",
        "Researchers recommend additional energy monitoring before expanding the university program.",
    ]
    text = " ".join(sentences)

    summary = service.summarize(text)

    assert summary
    positions = [text.index(sentence) for sentence in sentences if sentence in summary]
    assert positions
    assert positions == sorted(positions)


def test_document_classification_is_broad_and_confidence_is_bounded() -> None:
    category, confidence = NLPService.classify_document(
        "research-results.pdf",
        {"title": "Energy Research Paper", "subject": None},
        "Abstract Methodology Results Discussion References",
    )
    other, other_confidence = NLPService.classify_document(
        "notes.pdf",
        {},
        "A few miscellaneous thoughts without a recognizable structure.",
    )

    assert category == "Research Paper"
    assert 0 < confidence <= 1
    assert (other, other_confidence) == ("Other", 0.0)
