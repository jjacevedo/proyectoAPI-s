from pydantic import BaseModel, Field


class EvaluateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=12000)


class EvaluateResponse(BaseModel):
    prompt: str
    single_answer: str | None
    single_provider: str
    single_model: str
    single_tokens: int
    single_cost_estimated_usd: float | None
    single_latency_ms: float
    single_error: str | None
    multi_answer: str
    multi_tokens: int
    multi_cost_estimated_usd: float | None
    multi_latency_ms: float
    token_delta: int
    cost_delta_usd: float | None
    latency_delta_ms: float
    judge_verdict: str | None
    judge_reasoning: str | None
    judge_error: str | None
