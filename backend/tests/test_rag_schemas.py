import pytest
from pydantic import ValidationError

from backend.app.schemas.rag import (
    DocumentAgentRequest,
    DocumentAgentResponse,
    RagAnswer,
    RagQuestion,
    RagSource,
)


def test_document_agent_api_schemas_validate_text():
    request = DocumentAgentRequest(message="Search the contract")
    response = DocumentAgentResponse(answer="The period is 30 days.")

    assert request.message == "Search the contract"
    assert response.answer == "The period is 30 days."


@pytest.mark.parametrize(
    "model",
    [
        lambda: DocumentAgentRequest(message=""),
        lambda: DocumentAgentResponse(answer=""),
    ],
)
def test_document_agent_api_schemas_reject_empty_text(model):
    with pytest.raises(ValidationError):
        model()


def test_rag_question_uses_safe_defaults_and_limits():
    request = RagQuestion(question="What is the cancellation period?")

    assert request.limit == 3


@pytest.mark.parametrize(
    "payload",
    [
        {"question": ""},
        {"question": "valid", "limit": 0},
        {"question": "valid", "limit": 11},
    ],
)
def test_rag_question_rejects_invalid_input(payload):
    with pytest.raises(ValidationError):
        RagQuestion(**payload)


def test_rag_answer_validates_nested_sources():
    result = RagAnswer(
        answer="The synthetic contract allows cancellation within 30 days.",
        sources=[
            RagSource(
                chunk_id=10,
                document_submission_id=5,
                position=2,
            )
        ],
    )

    assert result.sources[0].chunk_id == 10
    assert result.sources[0].position == 2


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("chunk_id", 0),
        ("document_submission_id", 0),
        ("position", -1),
    ],
)
def test_rag_source_rejects_invalid_identifiers_or_position(field, value):
    data = {
        "chunk_id": 10,
        "document_submission_id": 5,
        "position": 2,
    }
    data[field] = value

    with pytest.raises(ValidationError):
        RagSource(**data)


def test_rag_answer_rejects_empty_answer():
    with pytest.raises(ValidationError):
        RagAnswer(answer="", sources=[])
