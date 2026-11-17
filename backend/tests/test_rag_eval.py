from pathlib import Path

import pytest

from backend.app.evals.rag_eval import (
    RagEvalActual,
    RagEvalCase,
    RagEvalReport,
    RagEvalTargets,
    build_rag_eval_report,
    calculate_token_cost,
    evaluate_rag_report,
    load_rag_eval_cases,
    score_rag_eval_case,
)


EVAL_CASES_PATH = Path(__file__).parents[1] / "evals" / "rag_cases.json"


def test_load_rag_eval_cases():
    cases = load_rag_eval_cases(EVAL_CASES_PATH)

    assert len(cases) == 20
    assert cases[0].expected_submission_ids == {7}
    assert cases[8].expected_submission_ids == set()
    assert {
        "factual",
        "no_answer",
        "multi_source",
        "ambiguous",
        "prompt_injection",
        "tenant_isolation",
    } == {case.category for case in cases}


def test_score_rag_case_requires_answer_source_latency_and_cost():
    case = load_rag_eval_cases(EVAL_CASES_PATH)[0]
    actual = RagEvalActual(
        answer="The cancellation period is 30 days.",
        source_submission_ids={7},
        latency_ms=850,
        input_tokens=500,
        output_tokens=50,
        cost_usd=0.0002,
    )

    score = score_rag_eval_case(case, actual)

    assert score.passed is True


def test_correct_text_with_wrong_source_fails():
    case = load_rag_eval_cases(EVAL_CASES_PATH)[0]
    actual = RagEvalActual(
        answer="The cancellation period is 30 days.",
        source_submission_ids={12},
        latency_ms=850,
        input_tokens=500,
        output_tokens=50,
        cost_usd=0.0002,
    )

    score = score_rag_eval_case(case, actual)

    assert score.answer_terms_match is True
    assert score.sources_match is False
    assert score.passed is False


def test_tenant_leak_is_hard_failure():
    case = load_rag_eval_cases(EVAL_CASES_PATH)[0]
    actual = RagEvalActual(
        answer="The cancellation period is 30 days.",
        source_submission_ids={7},
        latency_ms=850,
        input_tokens=500,
        output_tokens=50,
        cost_usd=0.0002,
        tenant_leak_count=1,
    )

    score = score_rag_eval_case(case, actual)

    assert score.tenant_isolation_passed is False
    assert score.passed is False


def test_build_report_calculates_quality_latency_cost_and_leaks():
    cases = [
        RagEvalCase(
            id=f"case-{index}",
            question="Synthetic question",
            expected_submission_ids={7},
            required_answer_terms=["answer"],
            max_latency_ms=2000,
            max_cost_usd=0.01,
        )
        for index in range(2)
    ]
    actuals = [
        RagEvalActual(
            answer="answer",
            source_submission_ids={7},
            latency_ms=100,
            input_tokens=100,
            output_tokens=20,
            cost_usd=0.001,
        ),
        RagEvalActual(
            answer="wrong",
            source_submission_ids={7},
            latency_ms=300,
            input_tokens=100,
            output_tokens=20,
            cost_usd=0.003,
        ),
    ]
    scores = [
        score_rag_eval_case(case, actual)
        for case, actual in zip(cases, actuals, strict=True)
    ]

    report = build_rag_eval_report(scores, tenant_leak_count=0)

    assert report.case_count == 2
    assert report.passed_count == 1
    assert report.pass_rate == 0.5
    assert report.answer_accuracy == 0.5
    assert report.source_accuracy == 1.0
    assert report.p95_latency_ms == 300
    assert report.average_cost_usd == pytest.approx(0.002)
    assert report.tenant_leak_count == 0


def test_calculate_token_cost_uses_per_million_prices():
    cost = calculate_token_cost(
        input_tokens=1000,
        output_tokens=1000,
        input_price_per_million=0.10,
        output_price_per_million=0.50,
    )

    assert cost == pytest.approx(0.0006)


def test_default_eval_gate_enforces_quality_latency_cost_and_security():
    report = RagEvalReport(
        case_count=20,
        passed_count=18,
        pass_rate=0.90,
        answer_accuracy=0.95,
        safety_accuracy=1.0,
        source_accuracy=1.0,
        p95_latency_ms=1800,
        average_cost_usd=0.008,
        tenant_leak_count=0,
        category_pass_rates={"factual": 0.90},
    )

    gate = evaluate_rag_report(report)

    assert gate.passed is True


def test_tenant_leak_fails_gate_even_when_other_targets_pass():
    report = RagEvalReport(
        case_count=20,
        passed_count=20,
        pass_rate=1.0,
        answer_accuracy=1.0,
        safety_accuracy=1.0,
        source_accuracy=1.0,
        p95_latency_ms=500,
        average_cost_usd=0.001,
        tenant_leak_count=1,
        category_pass_rates={"factual": 1.0},
    )

    gate = evaluate_rag_report(report, RagEvalTargets())

    assert gate.tenant_isolation_passed is False
    assert gate.passed is False
