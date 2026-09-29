"""Contracts for evidence-grounded answers and verification."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import settings
from app.schemas.retrieval import RetrievalMode


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    PARTIALLY_SUPPORTED = "partially_supported"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    UNVERIFIED = "unverified"


class AnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=settings.ANSWER_MAX_QUERY_LENGTH)
    document_ids: list[str] = Field(default_factory=list, max_length=100)
    retrieval_mode: RetrievalMode = RetrievalMode.HYBRID
    top_k: int = Field(
        default=settings.ANSWER_DEFAULT_TOP_K,
        ge=1,
        le=settings.ANSWER_MAX_TOP_K,
    )

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Query must not be blank")
        return value


class EvidenceSource(BaseModel):
    source_id: str = Field(pattern=r"^S[1-9][0-9]*$")
    document_id: str
    filename: str
    page_number: int = Field(ge=1)
    chunk_id: str
    text: str
    score: float = 0.0


class Citation(BaseModel):
    source_id: str
    document_id: str
    filename: str
    page_number: int
    chunk_id: str


class GroundedDraft(BaseModel):
    answer: str
    answerable: bool
    cited_source_ids: list[str] = Field(default_factory=list)


class ClaimVerification(BaseModel):
    claim: str
    supported: bool
    source_ids: list[str] = Field(default_factory=list)
    reason: str = Field(max_length=500)


class VerificationResult(BaseModel):
    status: VerificationStatus
    claims: list[ClaimVerification] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)


class AnswerResponse(BaseModel):
    query: str
    answer: str
    answerable: bool
    verification_status: VerificationStatus
    citations: list[Citation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    supported_claim_count: int = Field(default=0, ge=0)
    unsupported_claim_count: int = Field(default=0, ge=0)
