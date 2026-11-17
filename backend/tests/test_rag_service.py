from types import SimpleNamespace

import pytest

from backend.app.services.rag import (
    NO_RELEVANT_CONTEXT,
    RAG_INSTRUCTIONS,
    RAG_MODEL,
    GeneratedRagAnswer,
    answer_question_with_rag,
)
from backend.app.services.retrieval import DocumentChunk


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


def make_result():
    return (
        2,
        DocumentChunk(
            chunk_id=15,
            tenant_id=3,
            document_submission_id=7,
            content="The agreement may be cancelled within 30 days.",
            position=2,
        ),
    )


@pytest.mark.anyio
async def test_rag_service_returns_safe_answer_without_calling_model(
    monkeypatch,
):
    async def fake_retrieve(*args, **kwargs):
        return []

    monkeypatch.setattr(
        "backend.app.services.rag.retrieve_tenant_chunks",
        fake_retrieve,
    )
    client = FakeOpenAIClient(None)

    result = await answer_question_with_rag(
        "What is the cancellation period?",
        tenant_id=3,
        session=object(),
        client=client,
    )

    assert result.answer == NO_RELEVANT_CONTEXT
    assert result.sources == []
    assert client.responses.request is None


@pytest.mark.anyio
async def test_rag_service_uses_context_and_builds_sources_on_server(
    monkeypatch,
):
    async def fake_retrieve(*args, **kwargs):
        return [make_result()]

    monkeypatch.setattr(
        "backend.app.services.rag.retrieve_tenant_chunks",
        fake_retrieve,
    )
    client = FakeOpenAIClient(
        GeneratedRagAnswer(answer="The cancellation period is 30 days.")
    )

    result = await answer_question_with_rag(
        "What is the cancellation period?",
        tenant_id=3,
        session=object(),
        client=client,
    )

    assert result.answer == "The cancellation period is 30 days."
    assert result.sources[0].chunk_id == 15
    assert result.sources[0].document_submission_id == 7
    assert result.sources[0].position == 2
    request = client.responses.request
    assert request["model"] == RAG_MODEL
    assert request["instructions"] == RAG_INSTRUCTIONS
    assert "chunk_id=15" in request["input"]
    assert "cancelled within 30 days" in request["input"]
    assert request["text_format"] is GeneratedRagAnswer
    assert request["max_output_tokens"] == 500


@pytest.mark.anyio
async def test_rag_service_rejects_empty_question_before_dependencies(
    monkeypatch,
):
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("retrieval must not be called")

    monkeypatch.setattr(
        "backend.app.services.rag.retrieve_tenant_chunks",
        fail_if_called,
    )

    with pytest.raises(ValueError, match="question must not be empty"):
        await answer_question_with_rag(
            "   ",
            tenant_id=3,
            session=object(),
            client=FakeOpenAIClient(None),
        )


@pytest.mark.anyio
async def test_rag_service_rejects_missing_model_output(monkeypatch):
    async def fake_retrieve(*args, **kwargs):
        return [make_result()]

    monkeypatch.setattr(
        "backend.app.services.rag.retrieve_tenant_chunks",
        fake_retrieve,
    )

    with pytest.raises(ValueError, match="did not return"):
        await answer_question_with_rag(
            "What is the cancellation period?",
            tenant_id=3,
            session=object(),
            client=FakeOpenAIClient(None),
        )
