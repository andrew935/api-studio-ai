from backend.app.schemas.tool_approval import ToolApproval
from backend.app.services.tool_calling import TOOL_HANDLERS


approvals_store: dict[str, ToolApproval] = {}
agent_runs: dict[str, list[object]] = {}


def save_approval(approval: ToolApproval) -> None:
    approvals_store[approval.approval_id] = approval


def get_approval(approval_id: str) -> ToolApproval | None:
    return approvals_store.get(approval_id)


def save_agent_run(
    approval_id: str,
    input_items: list[object],
) -> None:
    agent_runs[approval_id] = list(input_items)


def get_agent_run(approval_id: str) -> list[object] | None:
    return agent_runs.get(approval_id)


def take_agent_run(approval_id: str) -> list[object] | None:
    return agent_runs.pop(approval_id, None)


def approve_tool(
    approval_id: str,
    current_user_id: int,
) -> ToolApproval:
    approval = get_approval(approval_id)

    if approval is None:
        raise KeyError("Approval not found")

    if approval.user_id != current_user_id:
        raise PermissionError(
            "Cannot approve another user's request"
        )

    if approval.status != "pending":
        raise RuntimeError("Approval is not pending")

    approval.status = "approved"
    return approval


async def execute_approved_tool(
    approval_id: str,
    current_user_id: int,
) -> object:
    approval = get_approval(approval_id)

    if approval is None:
        raise KeyError("Approval not found")

    if approval.user_id != current_user_id:
        raise PermissionError(
            "Cannot execute another user's request"
        )

    if approval.status != "approved":
        raise RuntimeError("Approval is not approved")

    tool_function = TOOL_HANDLERS.get(approval.tool_name)

    if tool_function is None:
        raise RuntimeError("Unknown tool")

    approval.status = "executing"

    try:
        result = await tool_function(**approval.arguments)
    except Exception:
        approval.status = "failed"
        raise

    approval.status = "completed"
    return result
