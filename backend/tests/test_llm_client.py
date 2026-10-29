from types import SimpleNamespace

import pytest

from backend.app.schemas.llm import SupportClassification
from backend.app.services.llm_client import (
    INSTRUCTIONS,
    MODEL,
    classify_support_message,
    create_openai_client,
)


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


def test_create_openai_client_passes_timeout_and_retries(monkeypatch):
    captured_options = {}
    expected_client = object()

    def fake_async_openai(**options):
        captured_options.update(options)
        return expected_client

    monkeypatch.setattr(
        "backend.app.services.llm_client.AsyncOpenAI",
        fake_async_openai,
    )

    client = create_openai_client(timeout=12.5, max_retries=4)

    assert client is expected_client
    assert captured_options == {
        "timeout": 12.5,
        "max_retries": 4,
    }


@pytest.mark.anyio
async def test_classify_support_message_returns_structured_output():
    expected = SupportClassification(
        category="billing",
        confidence=0.91,
        needs_human_review=False,
    )
    client = FakeOpenAIClient(expected)

    result = await classify_support_message("I was charged twice", client)

    assert result == expected
    assert client.responses.request == {
        "model": MODEL,
        "instructions": INSTRUCTIONS,
        "input": "I was charged twice",
        "text_format": SupportClassification,
        "max_output_tokens": 200,
    }


@pytest.mark.anyio
async def test_classify_support_message_rejects_empty_input():
    client = FakeOpenAIClient(None)

    with pytest.raises(ValueError, match="must not be empty"):
        await classify_support_message("   ", client)

    assert client.responses.request is None


@pytest.mark.anyio
async def test_classify_support_message_rejects_missing_output():
    client = FakeOpenAIClient(None)

    with pytest.raises(ValueError, match="did not return"):
        await classify_support_message("Help with my account", client)

