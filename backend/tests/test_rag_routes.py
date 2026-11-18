from fastapi.testclient import TestClient

from backend.app.api.dependencies import (
    get_current_tenant_id,
    get_database_session,
    get_openai_client,
)
from backend.app.main import app
from backend.app.schemas.rag import RagAnswer, RagSource


class FakeOpenAIClient:
    pass


def test_rag_route_uses_authenticated_tenant_and_returns_sources(monkeypatch):
    captured = {}

    async def fake_answer(question, **kwargs):
        captured["question"] = question
        captured.update(kwargs)
        return RagAnswer(
            answer="The cancellation period is 30 days.",
            sources=[
                RagSource(
                    chunk_id=15,
                    document_submission_id=7,
                    position=2,
                )
            ],
        )

    async def fake_session():
        yield object()

    monkeypatch.setattr(
        "backend.app.api.routes.ai.answer_question_with_rag",
        fake_answer,
    )
    app.dependency_overrides[get_current_tenant_id] = lambda: 3
    app.dependency_overrides[get_database_session] = fake_session
    app.dependency_overrides[get_openai_client] = FakeOpenAIClient

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/ai/rag/answer",
                json={
                    "question": "What is the cancellation period?",
                    "limit": 5,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "answer": "The cancellation period is 30 days.",
        "sources": [
            {
                "chunk_id": 15,
                "document_submission_id": 7,
                "position": 2,
            }
        ],
    }
    assert captured["question"] == "What is the cancellation period?"
    assert captured["tenant_id"] == 3
    assert captured["limit"] == 5


def test_rag_route_requires_authentication():
    app.dependency_overrides[get_openai_client] = FakeOpenAIClient

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/ai/rag/answer",
                json={"question": "What is the cancellation period?"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}


def test_rag_route_rejects_invalid_request_before_service(monkeypatch):
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("RAG service must not be called")

    monkeypatch.setattr(
        "backend.app.api.routes.ai.answer_question_with_rag",
        fail_if_called,
    )
    app.dependency_overrides[get_current_tenant_id] = lambda: 3
    app.dependency_overrides[get_openai_client] = FakeOpenAIClient

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/ai/rag/answer",
                json={"question": "valid", "limit": 0},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
