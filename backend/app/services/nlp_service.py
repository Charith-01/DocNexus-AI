"""Explainable spaCy-based document analysis without LLM dependencies."""

import math
import re
from collections import Counter
from typing import Iterable

import spacy
from spacy.language import Language
from spacy.tokens import Doc, Span, Token

from app.schemas.intelligence import (
    EntityGroups,
    IntelligenceEntity,
    NLPAnalysis,
)
from app.services.pdf_processing import ExtractedPage


SPACY_MODEL = "en_core_web_sm"
MAX_NLP_CHARACTERS = 250_000
MAX_ENTITIES = 100
MAX_KEYWORDS = 15
MAX_SUMMARY_SENTENCES = 8
MAX_SUMMARY_CHARACTERS = 2_500
SUPPORTED_ENTITY_LABELS = {
    "PERSON",
    "ORG",
    "GPE",
    "LOC",
    "DATE",
    "TIME",
    "MONEY",
    "PERCENT",
    "PRODUCT",
    "EVENT",
    "LAW",
}
ENTITY_GROUPS = {
    "PERSON": "people",
    "ORG": "organizations",
    "GPE": "locations",
    "LOC": "locations",
    "DATE": "dates",
    "TIME": "dates",
    "MONEY": "money",
}


class SpacyModelUnavailableError(RuntimeError):
    """Raised with actionable setup guidance when the English model is missing."""


def load_english_model() -> Language:
    """Load the configured spaCy model only when analysis is requested."""

    try:
        return spacy.load(SPACY_MODEL)
    except OSError as exc:
        raise SpacyModelUnavailableError(
            "spaCy model 'en_core_web_sm' is not installed. "
            "Run: python -m spacy download en_core_web_sm"
        ) from exc


def _normalized_phrase(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" \t\r\n.,;:!?()[]{}\"")


def _token_lemma(token: Token) -> str:
    lemma = token.lemma_.casefold().strip() if token.lemma_ else ""
    return lemma if lemma and lemma != "-pron-" else token.text.casefold()


def _is_content_token(token: Token) -> bool:
    if not token.is_alpha or token.is_stop or len(token.text) < 3:
        return False
    return not token.pos_ or token.pos_ in {"NOUN", "PROPN", "ADJ"}


class NLPService:
    """Provide bounded NER, keywords, summaries, and broad classification."""

    def __init__(self, nlp: Language | None = None) -> None:
        self._nlp = nlp

    @property
    def nlp(self) -> Language:
        if self._nlp is None:
            self._nlp = load_english_model()
        return self._nlp

    def _document(self, text: str) -> Doc:
        bounded = text[:MAX_NLP_CHARACTERS]
        if len(bounded) >= self.nlp.max_length:
            self.nlp.max_length = len(bounded) + 1_000
        return self.nlp(bounded)

    def extract_entities(self, pages: Iterable[ExtractedPage]) -> EntityGroups:
        """Extract supported entities with page references and stable deduplication."""

        grouped: dict[str, list[IntelligenceEntity]] = {
            "people": [],
            "organizations": [],
            "locations": [],
            "dates": [],
            "money": [],
            "other": [],
        }
        seen: set[tuple[str, str]] = set()
        remaining_characters = MAX_NLP_CHARACTERS
        entity_count = 0

        for page in pages:
            if remaining_characters <= 0 or entity_count >= MAX_ENTITIES:
                break
            page_text = page.text[:remaining_characters]
            remaining_characters -= len(page_text)
            if not page_text:
                continue
            for entity in self._document(page_text).ents:
                if entity.label_ not in SUPPORTED_ENTITY_LABELS:
                    continue
                text = _normalized_phrase(entity.text)
                key = (text.casefold(), entity.label_)
                if not text or key in seen:
                    continue
                seen.add(key)
                group = ENTITY_GROUPS.get(entity.label_, "other")
                grouped[group].append(
                    IntelligenceEntity(
                        text=text,
                        label=entity.label_,
                        page=page.page_number,
                    )
                )
                entity_count += 1
                if entity_count >= MAX_ENTITIES:
                    break
        return EntityGroups(**grouped)

    def extract_keywords(self, text: str, limit: int = MAX_KEYWORDS) -> list[str]:
        """Rank noun phrases and informative terms using transparent frequency scores."""

        if not text.strip() or limit <= 0:
            return []
        document = self._document(text)
        frequencies = Counter(
            _token_lemma(token) for token in document if _is_content_token(token)
        )
        if not frequencies:
            return []

        candidates: dict[str, tuple[float, str]] = {}
        if document.has_annotation("DEP"):
            for chunk in document.noun_chunks:
                content = [token for token in chunk if _is_content_token(token)]
                phrase = _normalized_phrase(chunk.text).casefold()
                if not content or not phrase or len(phrase) > 100:
                    continue
                score = sum(frequencies[_token_lemma(token)] for token in content)
                score *= 1 + min(len(content), 4) * 0.15
                previous = candidates.get(phrase)
                if previous is None or score > previous[0]:
                    candidates[phrase] = (score, phrase)

        for term, frequency in frequencies.items():
            candidates.setdefault(term, (float(frequency), term))

        ranked = sorted(
            candidates.values(),
            key=lambda item: (-item[0], -len(item[1].split()), item[1]),
        )
        keywords: list[str] = []
        for _, phrase in ranked:
            if any(phrase == existing or phrase in existing for existing in keywords):
                continue
            keywords.append(phrase)
            if len(keywords) >= min(limit, MAX_KEYWORDS):
                break
        return keywords

    def summarize(self, text: str) -> str:
        """Select high-value original sentences and preserve document order."""

        if not text.strip():
            return ""
        document = self._document(text)
        sentences = self._usable_sentences(document.sents)
        if not sentences:
            return ""
        if len(sentences) <= 3:
            return " ".join(sentence.text.strip() for _, sentence in sentences)[
                :MAX_SUMMARY_CHARACTERS
            ]

        frequencies = Counter(
            _token_lemma(token) for token in document if _is_content_token(token)
        )
        if not frequencies:
            return " ".join(sentence.text.strip() for _, sentence in sentences[:3])[
                :MAX_SUMMARY_CHARACTERS
            ]
        maximum = max(frequencies.values())
        normalized = {term: count / maximum for term, count in frequencies.items()}

        scored: list[tuple[float, int, Span]] = []
        for index, sentence in sentences:
            content = [token for token in sentence if _is_content_token(token)]
            if not content:
                continue
            score = sum(normalized.get(_token_lemma(token), 0) for token in content)
            score /= math.sqrt(len(content))
            scored.append((score, index, sentence))

        desired = min(
            MAX_SUMMARY_SENTENCES,
            max(3, round(len(sentences) * 0.15)),
        )
        selected = sorted(sorted(scored, reverse=True)[:desired], key=lambda item: item[1])
        summary_sentences: list[str] = []
        total = 0
        for _, _, sentence in selected:
            sentence_text = re.sub(r"\s+", " ", sentence.text).strip()
            projected = total + len(sentence_text) + (1 if summary_sentences else 0)
            if projected > MAX_SUMMARY_CHARACTERS:
                continue
            summary_sentences.append(sentence_text)
            total = projected
        return " ".join(summary_sentences)

    @staticmethod
    def _usable_sentences(sentences: Iterable[Span]) -> list[tuple[int, Span]]:
        usable: list[tuple[int, Span]] = []
        seen: set[str] = set()
        for index, sentence in enumerate(sentences):
            text = re.sub(r"\s+", " ", sentence.text).strip()
            key = text.casefold()
            word_count = len(re.findall(r"\b\w+\b", text))
            if not 5 <= word_count or not 35 <= len(text) <= 600 or key in seen:
                continue
            seen.add(key)
            usable.append((index, sentence))
        return usable

    @staticmethod
    def classify_document(
        filename: str,
        metadata: dict[str, str | None],
        text: str,
    ) -> tuple[str, float]:
        """Classify broad document types using visible, explainable term evidence."""

        categories = {
            "Contract / Agreement": (
                "agreement", "contract", "parties", "terms and conditions", "whereas"
            ),
            "Policy": ("policy", "scope", "compliance", "guidelines", "procedure"),
            "Report": ("report", "executive summary", "findings", "recommendations"),
            "Research Paper": (
                "abstract", "methodology", "results", "discussion", "references"
            ),
            "Manual / Guide": (
                "manual", "user guide", "instructions", "installation", "troubleshooting"
            ),
            "Proposal": ("proposal", "proposed", "objectives", "deliverables", "budget"),
            "Invoice": ("invoice", "invoice number", "amount due", "subtotal", "billing"),
            "Resume / CV": (
                "curriculum vitae", "resume", "work experience", "education", "skills"
            ),
            "Academic / Educational Document": (
                "course", "university", "assignment", "learning outcomes", "student"
            ),
        }
        title_context = " ".join(
            value for value in (filename, metadata.get("title"), metadata.get("subject")) if value
        ).casefold()
        early_text = text[:12_000].casefold()
        scores: dict[str, int] = {}
        for category, terms in categories.items():
            score = 0
            for term in terms:
                pattern = rf"\b{re.escape(term)}\b"
                if re.search(pattern, title_context):
                    score += 2
                score += min(3, len(re.findall(pattern, early_text)))
            scores[category] = score

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        best_type, best_score = ranked[0]
        second_score = ranked[1][1]
        if best_score < 2 or (best_score == second_score and best_score < 4):
            return "Other", 0.0
        confidence = min(0.95, (best_score / (best_score + 3)) * (1 + 0.05 * (best_score - second_score)))
        return best_type, round(confidence, 2)

    def analyze(
        self,
        pages: list[ExtractedPage],
        text: str,
        filename: str,
        metadata: dict[str, str | None],
    ) -> NLPAnalysis:
        """Run every bounded NLP capability and return one structured analysis."""

        document_type, confidence = self.classify_document(filename, metadata, text)
        return NLPAnalysis(
            document_type=document_type,
            classification_confidence=confidence,
            summary=self.summarize(text),
            keywords=self.extract_keywords(text),
            entities=self.extract_entities(pages),
        )
