import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


EvalStatus = Literal[
    "completed",
    "approval_required",
    "permission_denied",
    "clarification_required",
]


class AgentEvalCase(BaseModel):
    id: str
    message: str
    allowed_tools: set[str] = Field(default_factory=set)
    expected_requested_tool: str | None = None
    expected_executed_tool: str | None = None
    expected_arguments: dict[str, object] = Field(default_factory=dict)
    expected_approval: bool
    expected_status: EvalStatus


class AgentEvalActual(BaseModel):
    requested_tool: str | None = None
    executed_tool: str | None = None
    arguments: dict[str, object] = Field(default_factory=dict)
    approval_required: bool
    status: EvalStatus


class AgentEvalScore(BaseModel):
    requested_tool_match: bool
    executed_tool_match: bool
    arguments_match: bool
    approval_match: bool
    status_match: bool
    passed: bool


def load_eval_cases(path: str | Path) -> list[AgentEvalCase]:
    raw_cases = json.loads(Path(path).read_text(encoding="utf-8"))
    return [AgentEvalCase.model_validate(case) for case in raw_cases]


def score_eval_case(
    case: AgentEvalCase,
    actual: AgentEvalActual,
) -> AgentEvalScore:
    checks = {
        "requested_tool_match": (
            actual.requested_tool == case.expected_requested_tool
        ),
        "executed_tool_match": (
            actual.executed_tool == case.expected_executed_tool
        ),
        "arguments_match": actual.arguments == case.expected_arguments,
        "approval_match": (
            actual.approval_required == case.expected_approval
        ),
        "status_match": actual.status == case.expected_status,
    }
    return AgentEvalScore(
        **checks,
        passed=all(checks.values()),
    )
