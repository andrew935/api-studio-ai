import json
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from agents import (
    Agent,
    RunContextWrapper,
    RunState,
    Runner,
    SessionSettings,
    function_tool,
)
from agents.memory import SQLiteSession

from backend.app.schemas.tool_approval import ToolApproval
from backend.app.services.approval_store import (
    approve_tool,
    get_approval,
    save_approval,
)
from backend.app.services.llm_client import MODEL
from backend.app.services.tool_calling import (
    delete_customer,
    get_customer_balance,
)


@dataclass
class AppContext:
    user_id: int
    allowed_tools: set[str]


@dataclass
class PendingSdkRun:
    user_id: int
    state: RunState


pending_sdk_runs: dict[str, PendingSdkRun] = {}


@function_tool
async def sdk_get_customer_balance(
    customer_id: int,
) -> dict[str, int | float]:
    """Get a customer's balance by customer ID."""
    return await get_customer_balance(customer_id)


@function_tool(needs_approval=True)
async def sdk_delete_customer(
    context: RunContextWrapper[AppContext],
    customer_id: int,
) -> dict[str, int | str]:
    """Delete a customer by ID after permission and human approval."""
    if "sdk_delete_customer" not in context.context.allowed_tools:
        raise PermissionError("Tool is not permitted")

    return await delete_customer(customer_id)


support_agent = Agent(
    name="Customer Support",
    instructions=(
        "Help customers safely and use the balance tool when needed."
    ),
    model=MODEL,
    tools=[sdk_get_customer_balance],
)

approval_support_agent = Agent[AppContext](
    name="Customer Support With Approvals",
    instructions=(
        "Help customers safely. Use deletion only when explicitly requested."
    ),
    model=MODEL,
    tools=[sdk_get_customer_balance, sdk_delete_customer],
)


async def answer_with_sdk(message: str) -> str:
    """Run the SDK-managed agent loop and return its final text."""
    result = await Runner.run(
        support_agent,
        message,
        max_turns=5,
    )
    return str(result.final_output)


async def answer_with_sdk_session(
    message: str,
    conversation_id: str,
    db_path: str | Path = "agent_sessions.db",
) -> str:
    """Run the agent with SQLite-backed conversation history."""
    session = SQLiteSession(
        session_id=conversation_id,
        db_path=db_path,
        session_settings=SessionSettings(limit=20),
    )

    try:
        result = await Runner.run(
            support_agent,
            message,
            session=session,
            max_turns=5,
        )
    finally:
        session.close()

    return str(result.final_output)


async def start_sdk_agent(
    message: str,
    user_id: int,
    allowed_tools: set[str],
) -> str | ToolApproval:
    """Start an SDK agent run and pause if a tool needs approval."""
    context = AppContext(
        user_id=user_id,
        allowed_tools=set(allowed_tools),
    )
    result = await Runner.run(
        approval_support_agent,
        message,
        context=context,
        max_turns=5,
    )
    return _handle_sdk_result(result, user_id)


async def approve_and_resume_sdk_agent(
    approval_id: str,
    current_user_id: int,
    allowed_tools: set[str],
) -> str | ToolApproval:
    """Approve one permitted interruption and resume its SDK run."""
    approval = get_approval(approval_id)

    if approval is None:
        raise KeyError("Approval not found")

    if approval.user_id != current_user_id:
        raise PermissionError(
            "Cannot approve another user's request"
        )

    if approval.tool_name not in allowed_tools:
        raise PermissionError("Tool is not permitted")

    pending = pending_sdk_runs.get(approval_id)

    if pending is None:
        raise RuntimeError("SDK agent state not found")

    approved = approve_tool(approval_id, current_user_id)
    interruption = _find_interruption(
        pending.state,
        approved.call_id,
    )
    pending.state.approve(interruption)

    try:
        result = await Runner.run(
            approval_support_agent,
            pending.state,
            max_turns=5,
        )
    except Exception:
        approved.status = "failed"
        raise

    approved.status = "completed"
    pending_sdk_runs.pop(approval_id, None)
    return _handle_sdk_result(result, current_user_id)


def _handle_sdk_result(result, user_id: int) -> str | ToolApproval:
    if not result.interruptions:
        return str(result.final_output)

    interruption = result.interruptions[0]

    if interruption.tool_name is None:
        raise RuntimeError("Interrupted tool has no name")

    if interruption.call_id is None:
        raise RuntimeError("Interrupted tool has no call ID")

    arguments = json.loads(interruption.arguments or "{}")
    approval = ToolApproval(
        approval_id=str(uuid4()),
        user_id=user_id,
        tool_name=interruption.tool_name,
        arguments=arguments,
        call_id=interruption.call_id,
        status="pending",
    )
    save_approval(approval)
    pending_sdk_runs[approval.approval_id] = PendingSdkRun(
        user_id=user_id,
        state=result.to_state(),
    )
    return approval


def _find_interruption(state: RunState, call_id: str):
    for interruption in state.get_interruptions():
        if interruption.call_id == call_id:
            return interruption

    raise RuntimeError("SDK interruption not found")
