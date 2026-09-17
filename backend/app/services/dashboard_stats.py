from collections import defaultdict

from app.models.evaluation_log import EvaluationLog
from app.models.request_log import RequestLog
from app.schemas.dashboard import (
    ComplexityBreakdown,
    DashboardStats,
    EvaluationStats,
    TaskTypeBreakdown,
    VerificationStats,
)


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _avg_or_none(values: list[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return sum(present) / len(present) if present else None


def _pass_rate(verification_lists: list[list[dict]]) -> float | None:
    flattened = [item for sublist in verification_lists for item in sublist]
    if not flattened:
        return None
    passed = sum(1 for item in flattened if item.get("passed"))
    return passed / len(flattened)


def _task_type_breakdown(logs: list[RequestLog]) -> list[TaskTypeBreakdown]:
    groups: dict[str, list[RequestLog]] = defaultdict(list)
    for log in logs:
        groups[log.task_type].append(log)
    return [
        TaskTypeBreakdown(
            task_type=task_type,
            count=len(group),
            avg_tokens=_avg([log.tokens for log in group]),
            avg_cost_usd=_avg_or_none([log.cost_usd for log in group]),
            avg_latency_ms=_avg([log.latency_ms for log in group]),
        )
        for task_type, group in sorted(groups.items())
    ]


def _complexity_breakdown(logs: list[RequestLog]) -> list[ComplexityBreakdown]:
    groups: dict[str, list[RequestLog]] = defaultdict(list)
    for log in logs:
        groups[log.complexity].append(log)
    return [
        ComplexityBreakdown(
            complexity=complexity,
            count=len(group),
            avg_tokens=_avg([log.tokens for log in group]),
            avg_cost_usd=_avg_or_none([log.cost_usd for log in group]),
            avg_latency_ms=_avg([log.latency_ms for log in group]),
        )
        for complexity, group in sorted(groups.items())
    ]


def _verification_stats(logs: list[RequestLog]) -> VerificationStats:
    return VerificationStats(
        code_verification_pass_rate=_pass_rate([log.code_verifications for log in logs]),
        calculation_verification_pass_rate=_pass_rate([log.calculation_verifications for log in logs]),
        fact_search_result_count=sum(len(log.fact_search_results) for log in logs),
    )


def _evaluation_stats(evaluations: list[EvaluationLog]) -> EvaluationStats:
    cost_deltas = [
        evaluation.multi_cost_usd - evaluation.single_cost_usd
        for evaluation in evaluations
        if evaluation.multi_cost_usd is not None and evaluation.single_cost_usd is not None
    ]
    return EvaluationStats(
        total_evaluations=len(evaluations),
        multi_wins=sum(1 for evaluation in evaluations if evaluation.judge_verdict == "multi"),
        single_wins=sum(1 for evaluation in evaluations if evaluation.judge_verdict == "single"),
        ties=sum(1 for evaluation in evaluations if evaluation.judge_verdict == "tie"),
        judge_unavailable=sum(1 for evaluation in evaluations if evaluation.judge_verdict is None),
        avg_token_delta=_avg_or_none([evaluation.multi_tokens - evaluation.single_tokens for evaluation in evaluations]),
        avg_cost_delta_usd=_avg_or_none(cost_deltas),
        avg_latency_delta_ms=_avg_or_none(
            [evaluation.multi_latency_ms - evaluation.single_latency_ms for evaluation in evaluations]
        ),
    )


def compute_dashboard_stats(request_logs: list[RequestLog], evaluation_logs: list[EvaluationLog]) -> DashboardStats:
    costs = [log.cost_usd for log in request_logs if log.cost_usd is not None]
    return DashboardStats(
        total_requests=len(request_logs),
        total_tokens=sum(log.tokens for log in request_logs),
        total_cost_estimated_usd=sum(costs) if costs else None,
        avg_latency_ms=_avg([log.latency_ms for log in request_logs]) if request_logs else None,
        by_task_type=_task_type_breakdown(request_logs),
        by_complexity=_complexity_breakdown(request_logs),
        verification=_verification_stats(request_logs),
        evaluation=_evaluation_stats(evaluation_logs),
    )
