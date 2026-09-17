from pydantic import BaseModel


class TaskTypeBreakdown(BaseModel):
    task_type: str
    count: int
    avg_tokens: float
    avg_cost_usd: float | None
    avg_latency_ms: float


class ComplexityBreakdown(BaseModel):
    complexity: str
    count: int
    avg_tokens: float
    avg_cost_usd: float | None
    avg_latency_ms: float


class VerificationStats(BaseModel):
    code_verification_pass_rate: float | None
    calculation_verification_pass_rate: float | None
    fact_search_result_count: int


class EvaluationStats(BaseModel):
    total_evaluations: int
    multi_wins: int
    single_wins: int
    ties: int
    judge_unavailable: int
    avg_token_delta: float | None
    avg_cost_delta_usd: float | None
    avg_latency_delta_ms: float | None


class DashboardStats(BaseModel):
    total_requests: int
    total_tokens: int
    total_cost_estimated_usd: float | None
    avg_latency_ms: float | None
    by_task_type: list[TaskTypeBreakdown]
    by_complexity: list[ComplexityBreakdown]
    verification: VerificationStats
    evaluation: EvaluationStats
