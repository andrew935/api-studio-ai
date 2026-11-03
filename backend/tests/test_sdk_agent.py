from types import SimpleNamespace

import pytest
from agents.memory import SQLiteSession

from backend.app.services import sdk_agent
from backend.app.services.approval_store import approvals_store


class FakeInterruption:
    def __init__(self):
        self.tool_name = "sdk_delete_customer"
        self.arguments = '{"customer_id": 42}'
        self.call_id = "call_delete_42"


class FakeState:
    def __init__(self, interruption):
        self.interruption = interruption
        self.approved = []

    def get_interruptions(self):
        return [self.interruption]

    def approve(self, interruption):
        self.approved.append(interruption)


class FakeRunResult:
    def __init__(self, *, interruptions=None, final_output=None, state=None):
        self.interruptions = interruptions or []
        self.final_output = final_output
        self.state = state

    def to_state(self):
        return self.state


@pytest.fixture(autouse=True)
def clear_sdk_stores():
    approvals_store.clear()
    sdk_agent.pending_sdk_runs.clear()
    yield
    approvals_store.clear()
    sdk_agent.pending_sdk_runs.clear()


def test_sdk_tool_schema_is_generated_from_function_signature():
    assert sdk_agent.sdk_get_customer_balance.name == (
        "sdk_get_customer_balance"
    )
    assert sdk_agent.sdk_get_customer_balance.params_json_schema == {
        "properties": {
            "customer_id": {
                "title": "Customer Id",
                "type": "integer",
            }
        },
        "required": ["customer_id"],
        "title": "sdk_get_customer_balance_args",
        "type": "object",
        "additionalProperties": False,
    }


def test_sdk_delete_tool_requires_approval():
    assert sdk_agent.sdk_delete_customer.needs_approval is True


@pytest.mark.anyio
async def test_answer_with_sdk_uses_runner_without_live_api(monkeypatch):
    calls = []

    async def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(final_output="Customer balance is $150.00.")

    monkeypatch.setattr(sdk_agent.Runner, "run", fake_run)

    result = await sdk_agent.answer_with_sdk(
        "What is customer 42's balance?"
    )

    assert result == "Customer balance is $150.00."
    assert calls == [
        (
            (
                sdk_agent.support_agent,
                "What is customer 42's balance?",
            ),
            {"max_turns": 5},
        )
    ]


@pytest.mark.anyio
async def test_answer_with_sdk_session_persists_history(
    monkeypatch,
    tmp_path,
):
    db_path = tmp_path / "agent_sessions.db"

    async def fake_run(*args, **kwargs):
        session = kwargs["session"]
        await session.add_items(
            [
                {
                    "role": "user",
                    "content": "Remember customer 42",
                }
            ]
        )
        return SimpleNamespace(final_output="Remembered.")

    monkeypatch.setattr(sdk_agent.Runner, "run", fake_run)

    result = await sdk_agent.answer_with_sdk_session(
        "Remember customer 42",
        conversation_id="conversation_17",
        db_path=db_path,
    )

    reopened_session = SQLiteSession(
        session_id="conversation_17",
        db_path=db_path,
    )

    try:
        stored_items = await reopened_session.get_items()
    finally:
        reopened_session.close()

    assert result == "Remembered."
    assert stored_items == [
        {
            "role": "user",
            "content": "Remember customer 42",
        }
    ]


@pytest.mark.anyio
async def test_sdk_agent_pauses_approves_and_resumes(monkeypatch):
    interruption = FakeInterruption()
    state = FakeState(interruption)
    responses = [
        FakeRunResult(
            interruptions=[interruption],
            state=state,
        ),
        FakeRunResult(final_output="Customer 42 was deleted."),
    ]
    calls = []

    async def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return responses.pop(0)

    monkeypatch.setattr(sdk_agent.Runner, "run", fake_run)

    approval = await sdk_agent.start_sdk_agent(
        "Delete customer 42",
        user_id=17,
        allowed_tools={"sdk_delete_customer"},
    )

    assert approval.status == "pending"
    assert approval.arguments == {"customer_id": 42}

    result = await sdk_agent.approve_and_resume_sdk_agent(
        approval.approval_id,
        current_user_id=17,
        allowed_tools={"sdk_delete_customer"},
    )

    assert result == "Customer 42 was deleted."
    assert approval.status == "completed"
    assert state.approved == [interruption]
    assert approval.approval_id not in sdk_agent.pending_sdk_runs
    assert len(calls) == 2
    assert calls[1][0] == (sdk_agent.approval_support_agent, state)


@pytest.mark.anyio
async def test_sdk_agent_checks_permission_before_approval(monkeypatch):
    interruption = FakeInterruption()
    state = FakeState(interruption)

    async def fake_run(*args, **kwargs):
        return FakeRunResult(
            interruptions=[interruption],
            state=state,
        )

    monkeypatch.setattr(sdk_agent.Runner, "run", fake_run)
    approval = await sdk_agent.start_sdk_agent(
        "Delete customer 42",
        user_id=17,
        allowed_tools={"sdk_delete_customer"},
    )

    with pytest.raises(PermissionError, match="not permitted"):
        await sdk_agent.approve_and_resume_sdk_agent(
            approval.approval_id,
            current_user_id=17,
            allowed_tools=set(),
        )

    assert approval.status == "pending"
    assert state.approved == []


@pytest.mark.anyio
async def test_sdk_agent_rejects_another_user(monkeypatch):
    interruption = FakeInterruption()
    state = FakeState(interruption)

    async def fake_run(*args, **kwargs):
        return FakeRunResult(
            interruptions=[interruption],
            state=state,
        )

    monkeypatch.setattr(sdk_agent.Runner, "run", fake_run)
    approval = await sdk_agent.start_sdk_agent(
        "Delete customer 42",
        user_id=17,
        allowed_tools={"sdk_delete_customer"},
    )

    with pytest.raises(PermissionError, match="another user's request"):
        await sdk_agent.approve_and_resume_sdk_agent(
            approval.approval_id,
            current_user_id=99,
            allowed_tools={"sdk_delete_customer"},
        )

    assert approval.status == "pending"
    assert state.approved == []
