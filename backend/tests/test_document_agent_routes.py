from fastapi.testclient import TestClient

from backend.app.api.dependencies import (
    AuthenticatedUser,
    get_current_user,
    get_database_session,
)
from backend.app.main import app


def test_document_agent_route_uses_authenticated_server_context(monkeypatch):
    captured = {}
    session = object()

    async def fake_answer(message, **kwargs):
        captured["message"] = message
        captured.update(kwargs)
        return "The cancellation period is 30 days."

    async def fake_session():
        yield session

    monkeypatch.setattr(
        "backend.app.api.routes.ai.answer_with_document_agent",
        fake_answer,
    )
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        user_id=17,
        tenant_id=3,
        role="staff",
    )
    app.dependency_overrides[get_database_session] = fake_session

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/ai/agent/documents/answer",
                json={"message": "What is the cancellation period?"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "answer": "The cancellation period is 30 days."
    }
    assert captured == {
        "message": "What is the cancellation period?",
        "user_id": 17,
        "tenant_id": 3,
        "database_session": session,
        "allowed_tools": {"sdk_search_documents"},
    }


def test_document_agent_route_requires_authentication():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ai/agent/documents/answer",
            json={"message": "What is the cancellation period?"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}


def test_document_agent_route_rejects_invalid_request(monkeypatch):
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("agent service must not be called")

    monkeypatch.setattr(
        "backend.app.api.routes.ai.answer_with_document_agent",
        fail_if_called,
    )
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        user_id=17,
        tenant_id=3,
        role="staff",
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/ai/agent/documents/answer",
                json={"message": ""},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
