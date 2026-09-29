from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from fastapi.testclient import TestClient

from app.api import answers as answers_api
from app.auth.dependencies import get_current_user
from app.main import app
from app.core.config import settings
from app.schemas.answers import AnswerResponse, VerificationStatus
from app.services.llm_service import LLMProviderUnavailableError

client = TestClient(app)
USER_ID = ObjectId()


def current_user() -> dict[str, Any]:
    return {"_id": USER_ID, "email": "member4@example.com", "created_at": datetime.now(UTC)}


def test_answer_endpoint_requires_auth_and_forbids_spoofed_evidence():
    assert client.post("/answers/query", json={"query": "Question?"}).status_code == 401
    app.dependency_overrides[get_current_user] = current_user
    try:
        response = client.post(
            "/answers/query",
            json={"query": "Question?", "evidence": [{"text": "spoofed"}]},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422


def test_answer_request_validation_bounds():
    app.dependency_overrides[get_current_user] = current_user
    try:
        assert client.post("/answers/query", json={"query": " "}).status_code == 422
        assert client.post(
            "/answers/query", json={"query": "x" * (settings.ANSWER_MAX_QUERY_LENGTH + 1)}
        ).status_code == 422
        assert client.post("/answers/query", json={"query": "x", "top_k": 99}).status_code == 422
        assert client.post("/answers/query", json={"query": "x", "retrieval_mode": "invalid"}).status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_answer_response_serialization(monkeypatch):
    expected = AnswerResponse(
        query="Question?",
        answer="Grounded [S1]",
        answerable=True,
        verification_status=VerificationStatus.VERIFIED,
        citations=[],
    )
    monkeypatch.setattr(answers_api.answer_verification_agent, "answer", lambda *_: expected)
    app.dependency_overrides[get_current_user] = current_user
    try:
        response = client.post("/answers/query", json={"query": "Question?"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["verification_status"] == "verified"
    assert "GEMINI_API_KEY" not in response.text


def test_provider_failure_is_safe(monkeypatch):
    def fail(*_args):
        raise LLMProviderUnavailableError("provider unavailable")

    monkeypatch.setattr(answers_api.answer_verification_agent, "answer", fail)
    app.dependency_overrides[get_current_user] = current_user
    try:
        response = client.post("/answers/query", json={"query": "Question?"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.json() == {"detail": "LLM provider temporarily unavailable"}
