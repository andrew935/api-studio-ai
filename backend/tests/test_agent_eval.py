from pathlib import Path

from backend.app.evals.agent_eval import (
    AgentEvalActual,
    load_eval_cases,
    score_eval_case,
)


EVAL_CASES_PATH = (
    Path(__file__).parents[1] / "evals" / "agent_cases.json"
)


def test_load_eval_cases():
    cases = load_eval_cases(EVAL_CASES_PATH)

    assert len(cases) == 4
    assert cases[0].id == "balance_with_customer_id"
    assert cases[1].expected_arguments == {"customer_id": 42}


def test_score_eval_case_passes_exact_behavior():
    case = load_eval_cases(EVAL_CASES_PATH)[1]
    actual = AgentEvalActual(
        requested_tool="sdk_delete_customer",
        executed_tool=None,
        arguments={"customer_id": 42},
        approval_required=True,
        status="approval_required",
    )

    score = score_eval_case(case, actual)

    assert score.passed is True


def test_score_eval_case_detects_unsafe_execution():
    case = load_eval_cases(EVAL_CASES_PATH)[2]
    actual = AgentEvalActual(
        requested_tool="sdk_delete_customer",
        executed_tool="sdk_delete_customer",
        arguments={"customer_id": 42},
        approval_required=False,
        status="completed",
    )

    score = score_eval_case(case, actual)

    assert score.requested_tool_match is False
    assert score.executed_tool_match is False
    assert score.status_match is False
    assert score.passed is False
