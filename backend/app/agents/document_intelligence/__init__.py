"""Document Intelligence Agent public interface."""

from app.agents.document_intelligence.agent import (
    DocumentIntelligenceAgent,
    document_intelligence_agent,
    get_processed_pages,
    process_document_intelligence,
)

__all__ = [
    "DocumentIntelligenceAgent",
    "document_intelligence_agent",
    "get_processed_pages",
    "process_document_intelligence",
]
