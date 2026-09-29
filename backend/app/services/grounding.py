"""Evidence preparation and deterministic citation safeguards."""

from __future__ import annotations

import html
import re
from collections.abc import Iterable, Mapping
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

from app.schemas.answers import Citation, EvidenceSource, GroundedDraft, VerificationResult

CITATION_PATTERN = re.compile(r"\[(S[1-9][0-9]*)\]")


class CitationValidationError(ValueError):
    pass


def _safe_filename(value: Any) -> str:
    return PurePosixPath(PureWindowsPath(str(value)).name).name


def prepare_evidence(
    retrieved: Iterable[Mapping[str, Any]], max_characters: int
) -> list[EvidenceSource]:
    """Assign stable request-local IDs and retain only the highest-ranked context."""
    sources: list[EvidenceSource] = []
    remaining = max_characters
    for item in retrieved:
        text = str(item.get("text", "")).strip()
        if not text or remaining <= 0:
            continue
        selected = text[:remaining]
        sources.append(
            EvidenceSource(
                source_id=f"S{len(sources) + 1}",
                document_id=str(item["document_id"]),
                filename=_safe_filename(item["filename"]),
                page_number=int(item["page_number"]),
                chunk_id=str(item["chunk_id"]),
                text=selected,
                score=float(item.get("score", 0.0)),
            )
        )
        remaining -= len(selected)
    return sources


def format_evidence(sources: Iterable[EvidenceSource]) -> str:
    """Delimit untrusted document data so it cannot be confused with instructions."""
    blocks: list[str] = []
    for source in sources:
        blocks.append(
            f'<EVIDENCE source_id="{source.source_id}">\n'
            f"<DOCUMENT>{html.escape(source.filename)}</DOCUMENT>\n"
            f"<PAGE>{source.page_number}</PAGE>\n"
            f"<CHUNK_ID>{html.escape(source.chunk_id)}</CHUNK_ID>\n"
            f"<DOCUMENT_TEXT>{html.escape(source.text)}</DOCUMENT_TEXT>\n"
            "</EVIDENCE>"
        )
    return "\n\n".join(blocks)


def cited_source_ids(draft: GroundedDraft) -> list[str]:
    """Combine structured and inline citations, preserving order and removing duplicates."""
    ordered = [*draft.cited_source_ids, *CITATION_PATTERN.findall(draft.answer)]
    return list(dict.fromkeys(ordered))


def resolve_citations(
    draft: GroundedDraft, sources: Iterable[EvidenceSource]
) -> list[Citation]:
    """Resolve model source IDs exclusively through server-controlled metadata."""
    source_map = {source.source_id: source for source in sources}
    requested = cited_source_ids(draft)
    if draft.answerable and draft.answer.strip() and not requested:
        raise CitationValidationError("Generated answer did not cite evidence")
    unknown = [source_id for source_id in requested if source_id not in source_map]
    if unknown:
        raise CitationValidationError("Generated answer referenced an unknown source")
    return [
        Citation(
            source_id=source_id,
            document_id=source_map[source_id].document_id,
            filename=source_map[source_id].filename,
            page_number=source_map[source_id].page_number,
            chunk_id=source_map[source_id].chunk_id,
        )
        for source_id in requested
    ]


def validate_verification_sources(
    verification: VerificationResult, sources: Iterable[EvidenceSource]
) -> None:
    allowed = {source.source_id for source in sources}
    referenced = {
        source_id for claim in verification.claims for source_id in claim.source_ids
    }
    if not referenced.issubset(allowed):
        raise CitationValidationError("Verification referenced an unknown source")
