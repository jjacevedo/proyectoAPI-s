from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=12000)


class ProviderResponse(BaseModel):
    provider: str
    model: str
    content: str | None = None
    tokens: int = 0
    latency_ms: float = 0
    cost_estimated_usd: float | None = None
    error: str | None = None


class CritiqueResponse(BaseModel):
    provider: str
    model: str
    content: str | None = None
    reviewed_providers: list[str]
    tokens: int = 0
    latency_ms: float = 0
    cost_estimated_usd: float | None = None
    error: str | None = None


class CodeVerificationResponse(BaseModel):
    provider: str
    model: str
    passed: bool
    tests_run: int
    tests_passed: int
    tests_failed: int
    stdout: str
    stderr: str
    error: str | None = None
    timed_out: bool = False


class CalculationVerificationResponse(BaseModel):
    provider: str
    model: str
    passed: bool
    candidate_value: float | None = None
    reference_value: float | None = None
    difference: float | None = None
    error: str | None = None
    timed_out: bool = False


class FactCheckResultResponse(BaseModel):
    query: str
    title: str | None = None
    extract: str | None = None
    url: str | None = None
    error: str | None = None


class ChatResponse(BaseModel):
    final_answer: str
    responses: list[ProviderResponse]
    critiques: list[CritiqueResponse]
    revisions: list[ProviderResponse]
    models_used: list[str]
    total_tokens: int
    total_cost_estimated_usd: float | None
    latency_ms: float
    complexity: str
    routing_reason: str
    task_type: str
    disagreement_level: str
    disagreement_reason: str
    disagreement_evidence: list[str]
    generated_tests: str | None
    code_verifications: list[CodeVerificationResponse]
    reference_calculation: str | None
    calculation_verifications: list[CalculationVerificationResponse]
    fact_search_results: list[FactCheckResultResponse]
