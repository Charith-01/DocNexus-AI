"""Contracts shared by the orchestrator API and future agents."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Intent(StrEnum):
    SUMMARIZE_DOCUMENT = "summarize_document"
    ANALYZE_DOCUMENT = "analyze_document"
    SEARCH_DOCUMENTS = "search_documents"
    ASK_QUESTION = "ask_question"
    COMPARE_DOCUMENTS = "compare_documents"
    UNKNOWN = "unknown"


class AgentName(StrEnum):
    DOCUMENT_INTELLIGENCE = "document_intelligence"
    RETRIEVAL = "retrieval"
    ANSWER_VERIFICATION = "answer_verification"
    NONE = "none"


class AgentMessage(BaseModel):
    request_id: str
    user_id: str
    intent: Intent
    target_agent: AgentName
    payload: dict[str, Any] = Field(default_factory=dict)


class QueryRouteRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4_000)
    document_ids: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Query must not be blank")
        return value


class QueryRouteResponse(BaseModel):
    request_id: str
    intent: Intent
    target_agent: AgentName
    next_steps: list[AgentName]
