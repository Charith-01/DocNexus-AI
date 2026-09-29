"""Deterministic intent routing with replaceable agent integration points."""

from uuid import uuid4

from app.schemas.orchestrator import (
    AgentMessage,
    AgentName,
    Intent,
    QueryRouteRequest,
    QueryRouteResponse,
)


class QueryRouter:
    """Classify queries and describe which future agents should receive them."""

    def classify(self, query: str) -> Intent:
        normalized = query.casefold()

        if any(word in normalized for word in ("compare", "difference", "versus", " vs ")):
            return Intent.COMPARE_DOCUMENTS
        if any(word in normalized for word in ("summarize", "summary", "overview")):
            return Intent.SUMMARIZE_DOCUMENT
        if any(word in normalized for word in ("analyze", "analyse", "classify", "extract")):
            return Intent.ANALYZE_DOCUMENT
        if any(word in normalized for word in ("search", "find", "locate")):
            return Intent.SEARCH_DOCUMENTS

        question_starters = (
            "what ",
            "why ",
            "when ",
            "where ",
            "who ",
            "which ",
            "how ",
            "does ",
            "do ",
            "is ",
            "are ",
            "can ",
        )
        if "?" in normalized or normalized.startswith(question_starters):
            return Intent.ASK_QUESTION
        return Intent.UNKNOWN

    def route(
        self,
        request: QueryRouteRequest,
        user_id: str,
    ) -> tuple[AgentMessage, QueryRouteResponse]:
        """Build an agent message without invoking another member's agent."""

        intent = self.classify(request.query)
        target_agent, next_steps = self._workflow_for(intent)
        request_id = str(uuid4())
        message = AgentMessage(
            request_id=request_id,
            user_id=user_id,
            intent=intent,
            target_agent=target_agent,
            payload={
                "query": request.query,
                "document_ids": request.document_ids,
            },
        )
        response = QueryRouteResponse(
            request_id=request_id,
            intent=intent,
            target_agent=target_agent,
            next_steps=next_steps,
        )
        return message, response

    @staticmethod
    def _workflow_for(intent: Intent) -> tuple[AgentName, list[AgentName]]:
        workflows = {
            Intent.SUMMARIZE_DOCUMENT: (
                AgentName.DOCUMENT_INTELLIGENCE,
                [AgentName.DOCUMENT_INTELLIGENCE, AgentName.ANSWER_VERIFICATION],
            ),
            Intent.ANALYZE_DOCUMENT: (
                AgentName.DOCUMENT_INTELLIGENCE,
                [AgentName.DOCUMENT_INTELLIGENCE],
            ),
            Intent.SEARCH_DOCUMENTS: (
                AgentName.RETRIEVAL,
                [AgentName.RETRIEVAL],
            ),
            Intent.ASK_QUESTION: (
                AgentName.RETRIEVAL,
                [AgentName.RETRIEVAL, AgentName.ANSWER_VERIFICATION],
            ),
            Intent.COMPARE_DOCUMENTS: (
                AgentName.RETRIEVAL,
                [AgentName.RETRIEVAL, AgentName.ANSWER_VERIFICATION],
            ),
            Intent.UNKNOWN: (AgentName.NONE, []),
        }
        return workflows[intent]
