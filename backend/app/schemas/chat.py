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


class ChatResponse(BaseModel):
    final_answer: str
    responses: list[ProviderResponse]
    critiques: list[CritiqueResponse]
    models_used: list[str]
    total_tokens: int
    total_cost_estimated_usd: float | None
    latency_ms: float
    complexity: str
    routing_reason: str
