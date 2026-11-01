import json
from types import SimpleNamespace

import pytest

from backend.app.services.llm_client import MODEL
from backend.app.services.tool_calling import BALANCE_TOOL, answer_with_tools


class FakeResponses:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    async def create(self, **kwargs):
        self.requests.append(kwargs)
        return self.responses.pop(0)


class FakeOpenAIClient:
    def __init__(self, responses):
        self.responses = FakeResponses(responses)


@pytest.mark.anyio
async def test_answer_with_tools_returns_direct_answer_without_tool_call():
    first_response = SimpleNamespace(
        id="resp_direct",
        output=[],
        output_text="No tool is needed.",
    )
    client = FakeOpenAIClient([first_response])

    result = await answer_with_tools("Say hello", client)

    assert result == "No tool is needed."
    assert client.responses.requests == [
        {
            "model": MODEL,
            "input": "Say hello",
            "tools": [BALANCE_TOOL],
        }
    ]


@pytest.mark.anyio
async def test_answer_with_tools_executes_allowed_tool_and_returns_final_answer():
    tool_call = SimpleNamespace(
        type="function_call",
        name="get_customer_balance",
        arguments=json.dumps({"customer_id": 42}),
        call_id="call_balance_42",
    )
    first_response = SimpleNamespace(
        id="resp_tool_call",
        output=[tool_call],
        output_text="",
    )
    final_response = SimpleNamespace(
        id="resp_final",
        output=[],
        output_text="Customer 42 has a balance of $150.00.",
    )
    client = FakeOpenAIClient([first_response, final_response])

    result = await answer_with_tools("What is customer 42's balance?", client)

    assert result == "Customer 42 has a balance of $150.00."
    assert client.responses.requests == [
        {
            "model": MODEL,
            "input": "What is customer 42's balance?",
            "tools": [BALANCE_TOOL],
        },
        {
            "model": MODEL,
            "previous_response_id": "resp_tool_call",
            "input": [
                {
                    "type": "function_call_output",
                    "call_id": "call_balance_42",
                    "output": json.dumps(
                        {
                            "customer_id": 42,
                            "balance": 150.0,
                        }
                    ),
                }
            ],
            "tools": [BALANCE_TOOL],
        },
    ]


@pytest.mark.anyio
async def test_answer_with_tools_rejects_unknown_tool():
    tool_call = SimpleNamespace(
        type="function_call",
        name="delete_customer",
        arguments=json.dumps({"customer_id": 42}),
        call_id="call_unknown",
    )
    first_response = SimpleNamespace(
        id="resp_unknown",
        output=[tool_call],
        output_text="",
    )
    client = FakeOpenAIClient([first_response])

    with pytest.raises(ValueError, match="Unknown tool"):
        await answer_with_tools("Delete customer 42", client)
