"""Tests for deterministic query intent routing."""

import pytest

from app.agents.orchestrator import QueryRouter
from app.schemas.orchestrator import AgentName, Intent, QueryRouteRequest


@pytest.mark.parametrize(
    ("query", "intent", "agent"),
    [
        ("Summarize this contract", Intent.SUMMARIZE_DOCUMENT, AgentName.DOCUMENT_INTELLIGENCE),
        ("Analyze the parties", Intent.ANALYZE_DOCUMENT, AgentName.DOCUMENT_INTELLIGENCE),
        ("Find termination clauses", Intent.SEARCH_DOCUMENTS, AgentName.RETRIEVAL),
        ("What is the termination period?", Intent.ASK_QUESTION, AgentName.RETRIEVAL),
        ("Compare these agreements", Intent.COMPARE_DOCUMENTS, AgentName.RETRIEVAL),
        ("Hello there", Intent.UNKNOWN, AgentName.NONE),
    ],
)
def test_intent_routing(query: str, intent: Intent, agent: AgentName) -> None:
    _, response = QueryRouter().route(QueryRouteRequest(query=query), "user-id")

    assert response.intent == intent
    assert response.target_agent == agent
