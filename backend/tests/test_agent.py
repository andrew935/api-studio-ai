import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from backend.app.schemas.tool_approval import ToolApproval
from backend.app.services.agent import resume_agent, run_agent
from backend.app.services.approval_store import (
    agent_runs,
    approvals_store,
    approve_tool,
    get_agent_run,
    get_approval,
)
from backend.app.services.llm_client import MODEL
from backend.app.services.tool_calling import AGENT_TOOLS


class FakeResponses:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    async def create(self, **kwargs):
        self.requests.append(deepcopy(kwargs))
        return self.responses.pop(0)


class FakeOpenAIClient:
    def __init__(self, responses):
        self.responses = FakeResponses(responses)


def make_tool_call(customer_id: int, call_id: str):
    return SimpleNamespace(
        type="function_call",
        name="get_customer_balance",
        arguments=json.dumps({"customer_id": customer_id}),
        call_id=call_id,
    )


@pytest.fixture(autouse=True)
def clear_approvals_store():
    approvals_store.clear()
    agent_runs.clear()
    yield
    approvals_store.clear()
    agent_runs.clear()


@pytest.mark.anyio
async def test_run_agent_returns_direct_answer():
    final_response = SimpleNamespace(
        output=[],
        output_text="No tool is needed.",
    )
    client = FakeOpenAIClient([final_response])

    result = await run_agent("Say hello", client, user_id=17)

    assert result == "No tool is needed."
    assert len(client.responses.requests) == 1


@pytest.mark.anyio
async def test_run_agent_continues_across_multiple_tool_rounds():
    first_call = make_tool_call(42, "call_42")
    second_call = make_tool_call(7, "call_7")
    first_response = SimpleNamespace(output=[first_call], output_text="")
    second_response = SimpleNamespace(output=[second_call], output_text="")
    final_response = SimpleNamespace(
        output=[],
        output_text="Both customer balances are $150.00.",
    )
    client = FakeOpenAIClient(
        [first_response, second_response, final_response]
    )

    result = await run_agent(
        "Check customers 42 and 7",
        client,
        user_id=17,
    )

    assert result == "Both customer balances are $150.00."
    assert len(client.responses.requests) == 3

    second_input = client.responses.requests[1]["input"]
    assert second_input[-1] == {
        "type": "function_call_output",
        "call_id": "call_42",
        "output": json.dumps(
            {
                "customer_id": 42,
                "balance": 150.0,
            }
        ),
    }

    third_input = client.responses.requests[2]["input"]
    assert third_input[-1] == {
        "type": "function_call_output",
        "call_id": "call_7",
        "output": json.dumps(
            {
                "customer_id": 7,
                "balance": 150.0,
            }
        ),
    }
    assert client.responses.requests[0] == {
        "model": MODEL,
        "input": [
            {
                "role": "user",
                "content": "Check customers 42 and 7",
            }
        ],
        "tools": AGENT_TOOLS,
    }


@pytest.mark.anyio
async def test_run_agent_stops_before_tool_execution_at_step_limit():
    tool_call = make_tool_call(42, "call_limit")
    response = SimpleNamespace(output=[tool_call], output_text="")
    client = FakeOpenAIClient([response])

    with pytest.raises(
        RuntimeError,
        match="maximum number of steps",
    ):
        await run_agent(
            "Keep using tools",
            client,
            user_id=17,
            max_steps=1,
        )

    assert len(client.responses.requests) == 1


@pytest.mark.anyio
async def test_run_agent_pauses_before_sensitive_tool_execution():
    delete_call = SimpleNamespace(
        type="function_call",
        name="delete_customer",
        arguments=json.dumps({"customer_id": 42}),
        call_id="call_delete_42",
    )
    response = SimpleNamespace(output=[delete_call], output_text="")
    client = FakeOpenAIClient([response])

    result = await run_agent(
        "Delete customer 42",
        client,
        user_id=17,
    )

    assert isinstance(result, ToolApproval)
    assert result.user_id == 17
    assert result.tool_name == "delete_customer"
    assert result.arguments == {"customer_id": 42}
    assert result.call_id == "call_delete_42"
    assert result.status == "pending"
    assert get_approval(result.approval_id) is result
    assert get_agent_run(result.approval_id) is not None


@pytest.mark.anyio
async def test_resume_agent_continues_after_approved_tool():
    delete_call = SimpleNamespace(
        type="function_call",
        name="delete_customer",
        arguments=json.dumps({"customer_id": 42}),
        call_id="call_delete_42",
    )
    tool_response = SimpleNamespace(
        output=[delete_call],
        output_text="",
    )
    final_response = SimpleNamespace(
        output=[],
        output_text="Customer 42 was deleted.",
    )
    client = FakeOpenAIClient([tool_response, final_response])

    approval = await run_agent(
        "Delete customer 42",
        client,
        user_id=17,
    )
    assert isinstance(approval, ToolApproval)
    approve_tool(approval.approval_id, current_user_id=17)

    result = await resume_agent(
        approval.approval_id,
        current_user_id=17,
        client=client,
    )

    assert result == "Customer 42 was deleted."
    assert approval.status == "completed"
    assert get_agent_run(approval.approval_id) is None
    assert client.responses.requests[1]["input"][-1] == {
        "type": "function_call_output",
        "call_id": "call_delete_42",
        "output": json.dumps(
            {
                "customer_id": 42,
                "status": "deleted",
            }
        ),
    }


@pytest.mark.anyio
async def test_resume_agent_rejects_another_user():
    delete_call = SimpleNamespace(
        type="function_call",
        name="delete_customer",
        arguments=json.dumps({"customer_id": 42}),
        call_id="call_delete_42",
    )
    response = SimpleNamespace(output=[delete_call], output_text="")
    client = FakeOpenAIClient([response])
    approval = await run_agent(
        "Delete customer 42",
        client,
        user_id=17,
    )
    assert isinstance(approval, ToolApproval)
    approve_tool(approval.approval_id, current_user_id=17)

    with pytest.raises(PermissionError, match="another user's agent"):
        await resume_agent(
            approval.approval_id,
            current_user_id=99,
            client=client,
        )

    assert approval.status == "approved"
    assert get_agent_run(approval.approval_id) is not None
