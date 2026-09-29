"""Focused API security and behavior tests without a live MongoDB server."""

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from fastapi.testclient import TestClient

from app.api import auth as auth_api
from app.api import documents as documents_api
from app.api import orchestrator as orchestrator_api
from app.api import system as system_api
from app.auth.dependencies import get_current_user
from app.main import app


client = TestClient(app)
USER_ID = ObjectId("507f1f77bcf86cd799439011")
OTHER_USER_ID = ObjectId("507f191e810c19729de860ea")


def current_user() -> dict[str, Any]:
    return {
        "_id": USER_ID,
        "email": "member1@example.com",
        "created_at": datetime.now(UTC),
    }


def test_root_and_swagger_are_available() -> None:
    assert client.get("/").json() == {
        "message": "DocNexus AI API is running",
        "version": "0.1.0",
    }
    assert client.get("/docs").status_code == 200


def test_health_reports_connected_database(monkeypatch: Any) -> None:
    monkeypatch.setattr(system_api, "ping_database", lambda: True)

    assert client.get("/health").json() == {
        "status": "healthy",
        "database": "connected",
    }


def test_unauthenticated_document_access_is_rejected() -> None:
    response = client.get("/documents")

    assert response.status_code == 401


def test_duplicate_registration_is_rejected(monkeypatch: Any) -> None:
    class ExistingUsers:
        @staticmethod
        def find_one(*_: Any, **__: Any) -> dict[str, ObjectId]:
            return {"_id": USER_ID}

    monkeypatch.setattr(auth_api, "users_collection", ExistingUsers())
    response = client.post(
        "/auth/register",
        json={"email": "Member1@Example.com", "password": "password123"},
    )

    assert response.status_code == 409
    assert "password" not in response.text.casefold()


def test_user_cannot_access_another_users_document(monkeypatch: Any) -> None:
    class OtherUsersDocuments:
        @staticmethod
        def find_one(*_: Any, **__: Any) -> dict[str, Any]:
            return {
                "_id": ObjectId(),
                "owner_id": OTHER_USER_ID,
                "original_filename": "private.pdf",
            }

    app.dependency_overrides[get_current_user] = current_user
    monkeypatch.setattr(documents_api, "documents_collection", OtherUsersDocuments())
    monkeypatch.setattr(documents_api, "can_access_document", lambda *_: False)
    try:
        response = client.get(f"/documents/{ObjectId()}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_orchestrator_rejects_unauthorized_document_ids(monkeypatch: Any) -> None:
    class OtherUsersDocuments:
        @staticmethod
        def find_one(*_: Any, **__: Any) -> dict[str, Any]:
            return {"_id": ObjectId(), "owner_id": OTHER_USER_ID}

    app.dependency_overrides[get_current_user] = current_user
    monkeypatch.setattr(orchestrator_api, "documents_collection", OtherUsersDocuments())
    monkeypatch.setattr(orchestrator_api, "can_access_document", lambda *_: False)
    try:
        response = client.post(
            "/orchestrator/route",
            json={"query": "What is the term?", "document_ids": [str(ObjectId())]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
