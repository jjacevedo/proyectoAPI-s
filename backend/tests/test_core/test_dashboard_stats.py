from app.models.evaluation_log import EvaluationLog
from app.models.request_log import RequestLog
from app.services.dashboard_stats import compute_dashboard_stats


def make_request_log(**overrides) -> RequestLog:
    defaults = dict(
        tokens=100,
        cost_usd=0.01,
        latency_ms=500.0,
        task_type="general",
        complexity="low",
        code_verifications=[],
        calculation_verifications=[],
        fact_search_results=[],
    )
    defaults.update(overrides)
    return RequestLog(**defaults)


def make_evaluation_log(**overrides) -> EvaluationLog:
    defaults = dict(
        single_tokens=10,
        single_cost_usd=0.001,
        single_latency_ms=100.0,
        multi_tokens=40,
        multi_cost_usd=0.004,
        multi_latency_ms=400.0,
        judge_verdict=None,
    )
    defaults.update(overrides)
    return EvaluationLog(**defaults)


def test_empty_logs_produce_zeroed_stats():
    stats = compute_dashboard_stats([], [])

    assert stats.total_requests == 0
    assert stats.total_tokens == 0
    assert stats.total_cost_estimated_usd is None
    assert stats.avg_latency_ms is None
    assert stats.by_task_type == []
    assert stats.by_complexity == []
    assert stats.verification.code_verification_pass_rate is None
    assert stats.evaluation.total_evaluations == 0


def test_aggregates_totals_and_breakdowns():
    logs = [
        make_request_log(tokens=100, cost_usd=0.01, latency_ms=500.0, task_type="code", complexity="low"),
        make_request_log(tokens=300, cost_usd=0.03, latency_ms=1500.0, task_type="code", complexity="high"),
        make_request_log(tokens=200, cost_usd=None, latency_ms=1000.0, task_type="math", complexity="low"),
    ]

    stats = compute_dashboard_stats(logs, [])

    assert stats.total_requests == 3
    assert stats.total_tokens == 600
    assert stats.total_cost_estimated_usd == 0.04
    assert stats.avg_latency_ms == 1000.0

    task_types = {breakdown.task_type: breakdown for breakdown in stats.by_task_type}
    assert task_types["code"].count == 2
    assert task_types["code"].avg_tokens == 200.0
    assert task_types["math"].count == 1
    assert task_types["math"].avg_cost_usd is None

    complexities = {breakdown.complexity: breakdown for breakdown in stats.by_complexity}
    assert complexities["low"].count == 2
    assert complexities["high"].count == 1


def test_verification_pass_rate_across_candidates():
    logs = [
        make_request_log(code_verifications=[{"passed": True}, {"passed": False}]),
        make_request_log(code_verifications=[{"passed": True}]),
        make_request_log(calculation_verifications=[{"passed": False}]),
    ]

    stats = compute_dashboard_stats(logs, [])

    assert stats.verification.code_verification_pass_rate == 2 / 3
    assert stats.verification.calculation_verification_pass_rate == 0.0


def test_fact_search_result_count_sums_across_logs():
    logs = [
        make_request_log(fact_search_results=[{"query": "a"}, {"query": "b"}]),
        make_request_log(fact_search_results=[{"query": "c"}]),
    ]

    stats = compute_dashboard_stats(logs, [])

    assert stats.verification.fact_search_result_count == 3


def test_evaluation_stats_counts_verdicts_and_deltas():
    evaluations = [
        make_evaluation_log(judge_verdict="multi", single_tokens=10, multi_tokens=40),
        make_evaluation_log(judge_verdict="single", single_tokens=20, multi_tokens=30),
        make_evaluation_log(judge_verdict="tie"),
        make_evaluation_log(judge_verdict=None),
    ]

    stats = compute_dashboard_stats([], evaluations)

    assert stats.evaluation.total_evaluations == 4
    assert stats.evaluation.multi_wins == 1
    assert stats.evaluation.single_wins == 1
    assert stats.evaluation.ties == 1
    assert stats.evaluation.judge_unavailable == 1
    # deltas: 40-10=30, 30-20=10, and two defaults (40-10=30 each) -> avg 100/4
    assert stats.evaluation.avg_token_delta == 25.0


def test_evaluation_cost_delta_ignores_missing_costs():
    evaluations = [
        make_evaluation_log(single_cost_usd=0.001, multi_cost_usd=0.004),
        make_evaluation_log(single_cost_usd=None, multi_cost_usd=0.01),
    ]

    stats = compute_dashboard_stats([], evaluations)

    assert stats.evaluation.avg_cost_delta_usd == 0.003
