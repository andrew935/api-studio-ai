from typing import Literal

from pydantic import BaseModel


ApprovalStatus = Literal[
    "pending",
    "approved",
    "rejected",
    "executing",
    "completed",
    "failed",
]


class ToolApproval(BaseModel):
    approval_id: str
    user_id: int
    tool_name: str
    arguments: dict[str, object]
    call_id: str
    status: ApprovalStatus
