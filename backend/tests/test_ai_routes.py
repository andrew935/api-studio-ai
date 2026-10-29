from types import SimpleNamespace

import httpx2
import openai
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.llm import SupportClassification
from backend.app.services.llm_client import create_openai_client


class FakeResponses:
    def __init__(self, output_parsed):
        self.output_parsed = output_parsed
        self.request = None

    async def parse(self, **kwargs):
        self.request = kwargs
        return SimpleNamespace(output_parsed=self.output_parsed)


class FakeOpenAIClient:
    def __init__(self, output_parsed):
        self.responses = FakeResponses(output_parsed)


@pytest.fixture
def openai_client():
    return FakeOpenAIClient(
        SupportClassification(
            category="technical",
            confidence=0.88,
            needs_human_review=False,
        )
    )


@pytest.fixture
def client(openai_client):
    app.dependency_overrides[create_openai_client] = lambda: openai_client
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_classify_support_returns_structured_response(client, openai_client):
    response = client.post(
        "/api/v1/ai/classify",
        json={"message": "The application crashes when I sign in"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "category": "technical",
        "confidence": 0.88,
        "needs_human_review": False,
    }
    assert openai_client.responses.request["input"] == (
        "The application crashes when I sign in"
    )


@pytest.mark.parametrize("payload", [{}, {"message": ""}, {"message": 123}])
def test_classify_support_rejects_invalid_input(client, payload):
    response = client.post("/api/v1/ai/classify", json=payload)

    assert response.status_code == 422


REQUEST = httpx2.Request("POST", "https://api.openai.com/v1/responses")


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail"),
    [
        (
            openai.APITimeoutError(REQUEST),
            504,
            "OpenAI request timed out",
        ),
        (
            openai.APIConnectionError(request=REQUEST),
            502,
            "OpenAI request connection error",
        ),
        (
            openai.RateLimitError(
                "Rate limit exceeded",
                response=httpx2.Response(429, request=REQUEST),
                body=None,
            ),
            503,
            "OpenAI request rate limit error",
        ),
        (
            openai.APIError("OpenAI error", REQUEST, body=None),
            500,
            "OpenAI request API error",
        ),
    ],
)
def test_classify_support_maps_openai_errors(
    client,
    monkeypatch,
    error,
    expected_status,
    expected_detail,
):
    async def raise_openai_error(*args):
        raise error

    monkeypatch.setattr(
        "backend.app.api.routes.ai.classify_support_message",
        raise_openai_error,
    )

    response = client.post(
        "/api/v1/ai/classify",
        json={"message": "Help with my account"},
    )

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}

