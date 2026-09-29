"""Grounded answer orchestration over Member 3 authorized evidence."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from bson import ObjectId

from app.agents.retrieval.agent import information_retrieval_agent
from app.core.config import settings
from app.schemas.answers import (
    AnswerRequest,
    AnswerResponse,
    Citation,
    GroundedDraft,
    VerificationResult,
    VerificationStatus,
)
from app.schemas.retrieval import RetrievalSearchRequest
from app.services.grounding import (
    CitationValidationError,
    format_evidence,
    prepare_evidence,
    resolve_citations,
    validate_verification_sources,
)
from app.services.llm_service import GeminiService, LLMServiceError, gemini_service

INSUFFICIENT_ANSWER = (
    "I could not find sufficient information in the available documents "
    "to answer this question."
)

EvidenceRetriever = Callable[[AnswerRequest, ObjectId], list[dict[str, Any]]]


def retrieve_answer_evidence(request: AnswerRequest, user_id: ObjectId) -> list[dict[str, Any]]:
    """Use Member 3's authorization-aware agent; never access Chroma directly."""
    response = information_retrieval_agent.search(
        RetrievalSearchRequest(
            query=request.query,
            document_ids=request.document_ids,
            mode=request.retrieval_mode,
            top_k=request.top_k,
        ),
        user_id,
    )
    evidence: list[dict[str, Any]] = []
    for item in response.results:
        score = item.hybrid_score
        if score is None:
            score = item.semantic_score if item.semantic_score is not None else item.bm25_score
        evidence.append(
            {
                "chunk_id": item.chunk_id,
                "document_id": item.document_id,
                "filename": item.filename,
                "page_number": item.page_number,
                "text": item.text,
                "score": score or 0.0,
            }
        )
    return evidence


class AnswerVerificationAgent:
    """Generate, validate, verify, and at most once repair grounded answers."""

    def __init__(
        self,
        llm: GeminiService = gemini_service,
        retriever: EvidenceRetriever = retrieve_answer_evidence,
    ) -> None:
        self.llm = llm
        self.retriever = retriever

    @staticmethod
    def _insufficient(query: str, warnings: list[str] | None = None) -> AnswerResponse:
        return AnswerResponse(
            query=query,
            answer=INSUFFICIENT_ANSWER,
            answerable=False,
            verification_status=VerificationStatus.INSUFFICIENT_EVIDENCE,
            warnings=warnings or [],
        )

    @staticmethod
    def _counts(verification: VerificationResult) -> tuple[int, int]:
        supported = sum(claim.supported for claim in verification.claims)
        unsupported = sum(not claim.supported for claim in verification.claims)
        unsupported = max(unsupported, len(verification.unsupported_claims))
        return supported, unsupported

    @staticmethod
    def _effective_status(verification: VerificationResult) -> VerificationStatus:
        _, unsupported = AnswerVerificationAgent._counts(verification)
        if unsupported and verification.status == VerificationStatus.VERIFIED:
            return VerificationStatus.PARTIALLY_SUPPORTED
        return verification.status

    def _final_response(
        self,
        query: str,
        draft: GroundedDraft,
        citations: list[Citation],
        verification: VerificationResult,
        warnings: list[str],
    ) -> AnswerResponse:
        status = self._effective_status(verification)
        if status == VerificationStatus.INSUFFICIENT_EVIDENCE or not draft.answerable:
            return self._insufficient(query, warnings)
        supported, unsupported = self._counts(verification)
        if status != VerificationStatus.VERIFIED:
            warnings.append("Some answer claims could not be fully verified against the evidence.")
        return AnswerResponse(
            query=query,
            answer=draft.answer,
            answerable=True,
            verification_status=status,
            citations=citations,
            warnings=list(dict.fromkeys(warnings)),
            supported_claim_count=supported,
            unsupported_claim_count=unsupported,
        )

    def answer(self, request: AnswerRequest, user_id: ObjectId) -> AnswerResponse:
        raw_evidence = self.retriever(request, user_id)
        sources = prepare_evidence(raw_evidence, settings.ANSWER_MAX_EVIDENCE_CHARS)
        if not sources:
            return self._insufficient(request.query)
        evidence_text = format_evidence(sources)
        draft = self.llm.generate_grounded_answer(request.query, evidence_text)
        if not draft.answerable or not draft.answer.strip():
            return self._insufficient(request.query)

        warnings: list[str] = []
        repair_reason: list[str] = []
        try:
            citations = resolve_citations(draft, sources)
        except CitationValidationError:
            citations = []
            repair_reason = ["The draft used missing or invalid source citations."]

        verification: VerificationResult | None = None
        if not repair_reason:
            try:
                verification = self.llm.verify_answer(
                    request.query, draft.answer, evidence_text
                )
                validate_verification_sources(verification, sources)
                if self._effective_status(verification) != VerificationStatus.VERIFIED:
                    repair_reason = verification.unsupported_claims or [
                        "The draft was not fully supported by the evidence."
                    ]
            except (LLMServiceError, CitationValidationError):
                warnings.append("The answer could not be fully verified.")
                return AnswerResponse(
                    query=request.query,
                    answer=draft.answer,
                    answerable=True,
                    verification_status=VerificationStatus.UNVERIFIED,
                    citations=citations,
                    warnings=warnings,
                )

        if not repair_reason and verification is not None:
            return self._final_response(
                request.query, draft, citations, verification, warnings
            )

        repaired = self.llm.repair_answer(
            request.query, draft.answer, evidence_text, repair_reason
        )
        if not repaired.answerable or not repaired.answer.strip():
            return self._insufficient(request.query, ["The initial answer was not supported."])
        try:
            repaired_citations = resolve_citations(repaired, sources)
            repaired_verification = self.llm.verify_answer(
                request.query, repaired.answer, evidence_text
            )
            validate_verification_sources(repaired_verification, sources)
        except CitationValidationError:
            return AnswerResponse(
                query=request.query,
                answer="I could not produce a reliably cited answer from the available evidence.",
                answerable=False,
                verification_status=VerificationStatus.UNVERIFIED,
                warnings=["The repaired answer contained invalid citations."],
            )
        except LLMServiceError:
            return AnswerResponse(
                query=request.query,
                answer=repaired.answer,
                answerable=True,
                verification_status=VerificationStatus.UNVERIFIED,
                citations=repaired_citations,
                warnings=["The repaired answer could not be verified."],
            )
        return self._final_response(
            request.query,
            repaired,
            repaired_citations,
            repaired_verification,
            warnings,
        )


answer_verification_agent = AnswerVerificationAgent()


def answer_document_question(
    query: str,
    user_id: ObjectId,
    document_ids: list[str] | None = None,
    top_k: int = settings.ANSWER_DEFAULT_TOP_K,
) -> AnswerResponse:
    """Stable Member 1 integration hook for question and comparison workflows."""
    return answer_verification_agent.answer(
        AnswerRequest(query=query, document_ids=document_ids or [], top_k=top_k),
        user_id,
    )
