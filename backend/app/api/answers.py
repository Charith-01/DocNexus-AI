"""Authenticated document-grounded answer API."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.agents.answer_verification.agent import answer_verification_agent
from app.agents.retrieval.agent import (
    DocumentAccessDeniedError,
    DocumentNotFoundError,
    InvalidDocumentIdError,
    RetrievalError,
)
from app.auth.dependencies import get_current_user
from app.schemas.answers import AnswerRequest, AnswerResponse
from app.services.llm_service import (
    LLMConfigurationError,
    LLMInvalidResponseError,
    LLMProviderUnavailableError,
)

router = APIRouter(prefix="/answers", tags=["Answer & Verification"])


@router.post("/query", response_model=AnswerResponse)
def answer_query(
    request: AnswerRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> AnswerResponse:
    try:
        return answer_verification_agent.answer(request, current_user["_id"])
    except (InvalidDocumentIdError, DocumentNotFoundError) as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc
    except DocumentAccessDeniedError as exc:
        raise HTTPException(status_code=403, detail="Document access denied") from exc
    except RetrievalError as exc:
        raise HTTPException(status_code=500, detail="Retrieval operation failed") from exc
    except (LLMConfigurationError, LLMProviderUnavailableError) as exc:
        raise HTTPException(
            status_code=503, detail="LLM provider temporarily unavailable"
        ) from exc
    except LLMInvalidResponseError as exc:
        raise HTTPException(status_code=502, detail="LLM provider returned an invalid response") from exc
