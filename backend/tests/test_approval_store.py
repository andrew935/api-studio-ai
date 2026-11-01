import pytest

from backend.app.schemas.tool_approval import ToolApproval
from backend.app.services.approval_store import (
    approvals_store,
    approve_tool,
    execute_approved_tool,
    get_approval,
    save_approval,
)
from backend.app.services.tool_calling import TOOL_HANDLERS


@pytest.fixture(autouse=True)
def clear_approvals_store():
    approvals_store.clear()
    yield
    approvals_store.clear()


def make_approval(
    *,
    status: str = "pending",
) -> ToolApproval:
    return ToolApproval(
        approval_id="approval_42",
        user_id=17,
        tool_name="delete_customer",
        arguments={"customer_id": 42},
        call_id="call_42",
        status=status,
    )


def test_save_and_get_approval():
    approval = make_approval()

    save_approval(approval)

    assert get_approval("approval_42") is approval
    assert get_approval("missing") is None


def test_approve_tool_checks_owner_and_pending_status():
    approval = make_approval()
    save_approval(approval)

    with pytest.raises(PermissionError):
        approve_tool("approval_42", current_user_id=99)

    approved = approve_tool("approval_42", current_user_id=17)

    assert approved.status == "approved"

    with pytest.raises(RuntimeError, match="not pending"):
        approve_tool("approval_42", current_user_id=17)


def test_approve_tool_rejects_unknown_approval():
    with pytest.raises(KeyError, match="Approval not found"):
        approve_tool("missing", current_user_id=17)


@pytest.mark.anyio
async def test_execute_approved_tool():
    approval = make_approval(status="approved")
    save_approval(approval)

    result = await execute_approved_tool(
        "approval_42",
        current_user_id=17,
    )

    assert result == {
        "customer_id": 42,
        "status": "deleted",
    }
    assert approval.status == "completed"


@pytest.mark.anyio
async def test_execute_tool_requires_approval_and_owner():
    approval = make_approval()
    save_approval(approval)

    with pytest.raises(RuntimeError, match="not approved"):
        await execute_approved_tool(
            "approval_42",
            current_user_id=17,
        )

    approval.status = "approved"

    with pytest.raises(PermissionError):
        await execute_approved_tool(
            "approval_42",
            current_user_id=99,
        )


@pytest.mark.anyio
async def test_execute_tool_marks_failed_status(monkeypatch):
    async def failing_delete_customer(customer_id: int):
        raise RuntimeError(f"Could not delete customer {customer_id}")

    monkeypatch.setitem(
        TOOL_HANDLERS,
        "delete_customer",
        failing_delete_customer,
    )
    approval = make_approval(status="approved")
    save_approval(approval)

    with pytest.raises(RuntimeError, match="Could not delete"):
        await execute_approved_tool(
            "approval_42",
            current_user_id=17,
        )

    assert approval.status == "failed"
