"""API tests for Document Intelligence authorization and safe errors."""

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from fastapi.testclient import TestClient

from app.agents.document_intelligence.agent import (
    DocumentAccessDeniedError,
    InvalidDocumentIdError,
)
from app.api import intelligence as intelligence_api
from app.auth.dependencies import get_current_user
from app.main import app


client = TestClient(app)
USER_ID = ObjectId("507f1f77bcf86cd799439011")


def current_user() -> dict[str, Any]:
    return {
        "_id": USER_ID,
        "email": "member2@example.com",
        "created_at": datetime.now(UTC),
    }


def test_invalid_document_id_returns_not_found(monkeypatch: Any) -> None:
    class InvalidAgent:
        @staticmethod
        def process(*_: Any) -> None:
            raise InvalidDocumentIdError("Invalid document identifier")

    app.dependency_overrides[get_current_user] = current_user
    monkeypatch.setattr(intelligence_api, "document_intelligence_agent", InvalidAgent())
    try:
        response = client.post("/documents/not-an-object-id/process")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found"}


def test_unauthorized_user_cannot_read_intelligence(monkeypatch: Any) -> None:
    class DeniedAgent:
        @staticmethod
        def get_intelligence(*_: Any) -> None:
            raise DocumentAccessDeniedError("Document access denied")

    app.dependency_overrides[get_current_user] = current_user
    monkeypatch.setattr(intelligence_api, "document_intelligence_agent", DeniedAgent())
    try:
        response = client.get(f"/documents/{ObjectId()}/intelligence")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Document access denied"}
