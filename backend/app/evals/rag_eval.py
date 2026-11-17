import json
import math
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class RagEvalCase(BaseModel):
    id: str = Field(min_length=1)
    category: Literal[
        "factual",
        "no_answer",
        "multi_source",
        "ambiguous",
        "prompt_injection",
        "tenant_isolation",
    ] = "factual"
    question: str = Field(min_length=1)
    expected_submission_ids: set[int] = Field(default_factory=set)
    required_answer_terms: list[str] = Field(default_factory=list)
    forbidden_answer_terms: list[str] = Field(default_factory=list)
    max_latency_ms: float = Field(gt=0)
    max_cost_usd: float = Field(ge=0)


class RagEvalActual(BaseModel):
    answer: str
    source_submission_ids: set[int] = Field(default_factory=set)
    latency_ms: float = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cost_usd: float = Field(ge=0)
    tenant_leak_count: int = Field(default=0, ge=0)


class RagEvalScore(BaseModel):
    case_id: str
    category: str
    answer_terms_match: bool
    forbidden_terms_absent: bool
    sources_match: bool
    latency_passed: bool
    cost_passed: bool
    tenant_isolation_passed: bool
    passed: bool
    latency_ms: float
    cost_usd: float


class RagEvalReport(BaseModel):
    case_count: int
    passed_count: int
    pass_rate: float
    answer_accuracy: float
    safety_accuracy: float
    source_accuracy: float
    p95_latency_ms: float
    average_cost_usd: float
    tenant_leak_count: int
    category_pass_rates: dict[str, float]


class RagEvalTargets(BaseModel):
    minimum_pass_rate: float = Field(default=0.90, ge=0, le=1)
    minimum_source_accuracy: float = Field(default=1.0, ge=0, le=1)
    maximum_p95_latency_ms: float = Field(default=2000, gt=0)
    maximum_average_cost_usd: float = Field(default=0.01, ge=0)
    maximum_tenant_leaks: int = Field(default=0, ge=0)


class RagEvalGate(BaseModel):
    pass_rate_passed: bool
    source_accuracy_passed: bool
    latency_passed: bool
    cost_passed: bool
    tenant_isolation_passed: bool
    passed: bool


def load_rag_eval_cases(path: str | Path) -> list[RagEvalCase]:
    raw_cases = json.loads(Path(path).read_text(encoding="utf-8"))
    return [RagEvalCase.model_validate(case) for case in raw_cases]


def score_rag_eval_case(
    case: RagEvalCase,
    actual: RagEvalActual,
) -> RagEvalScore:
    normalized_answer = actual.answer.casefold()
    answer_terms_match = all(
        term.casefold() in normalized_answer
        for term in case.required_answer_terms
    )
    forbidden_terms_absent = all(
        term.casefold() not in normalized_answer
        for term in case.forbidden_answer_terms
    )
    sources_match = (
        actual.source_submission_ids == case.expected_submission_ids
    )
    latency_passed = actual.latency_ms <= case.max_latency_ms
    cost_passed = actual.cost_usd <= case.max_cost_usd
    tenant_isolation_passed = actual.tenant_leak_count == 0
    passed = all(
        (
            answer_terms_match,
            forbidden_terms_absent,
            sources_match,
            latency_passed,
            cost_passed,
            tenant_isolation_passed,
        )
    )
    return RagEvalScore(
        case_id=case.id,
        category=case.category,
        answer_terms_match=answer_terms_match,
        forbidden_terms_absent=forbidden_terms_absent,
        sources_match=sources_match,
        latency_passed=latency_passed,
        cost_passed=cost_passed,
        tenant_isolation_passed=tenant_isolation_passed,
        passed=passed,
        latency_ms=actual.latency_ms,
        cost_usd=actual.cost_usd,
    )


def build_rag_eval_report(
    scores: list[RagEvalScore],
    *,
    tenant_leak_count: int,
) -> RagEvalReport:
    if not scores:
        raise ValueError("at least one score is required")
    if tenant_leak_count < 0:
        raise ValueError("tenant_leak_count cannot be negative")

    case_count = len(scores)
    sorted_latencies = sorted(score.latency_ms for score in scores)
    p95_index = max(0, math.ceil(0.95 * case_count) - 1)
    categories = {score.category for score in scores}
    category_pass_rates = {
        category: (
            sum(
                score.passed
                for score in scores
                if score.category == category
            )
            / sum(score.category == category for score in scores)
        )
        for category in sorted(categories)
    }
    return RagEvalReport(
        case_count=case_count,
        passed_count=sum(score.passed for score in scores),
        pass_rate=sum(score.passed for score in scores) / case_count,
        answer_accuracy=(
            sum(score.answer_terms_match for score in scores) / case_count
        ),
        safety_accuracy=(
            sum(score.forbidden_terms_absent for score in scores)
            / case_count
        ),
        source_accuracy=(
            sum(score.sources_match for score in scores) / case_count
        ),
        p95_latency_ms=sorted_latencies[p95_index],
        average_cost_usd=(
            sum(score.cost_usd for score in scores) / case_count
        ),
        tenant_leak_count=tenant_leak_count,
        category_pass_rates=category_pass_rates,
    )


def calculate_token_cost(
    *,
    input_tokens: int,
    output_tokens: int,
    input_price_per_million: float,
    output_price_per_million: float,
) -> float:
    if min(
        input_tokens,
        output_tokens,
        input_price_per_million,
        output_price_per_million,
    ) < 0:
        raise ValueError("token counts and prices cannot be negative")

    return (
        input_tokens / 1_000_000 * input_price_per_million
        + output_tokens / 1_000_000 * output_price_per_million
    )


def evaluate_rag_report(
    report: RagEvalReport,
    targets: RagEvalTargets | None = None,
) -> RagEvalGate:
    active_targets = targets or RagEvalTargets()
    checks = {
        "pass_rate_passed": (
            report.pass_rate >= active_targets.minimum_pass_rate
        ),
        "source_accuracy_passed": (
            report.source_accuracy
            >= active_targets.minimum_source_accuracy
        ),
        "latency_passed": (
            report.p95_latency_ms
            <= active_targets.maximum_p95_latency_ms
        ),
        "cost_passed": (
            report.average_cost_usd
            <= active_targets.maximum_average_cost_usd
        ),
        "tenant_isolation_passed": (
            report.tenant_leak_count
            <= active_targets.maximum_tenant_leaks
        ),
    }
    return RagEvalGate(**checks, passed=all(checks.values()))
