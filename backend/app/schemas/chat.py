from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=12000)
    # Memoria de conversaciones (issue #16). Si se pasa conversation_id, el
    # mensaje se agrega a esa conversacion existente y "mode" se ignora (ya
    # quedo fijado al crearla). Si no, se crea una conversacion nueva con el
    # modo indicado (o "deliberation" si no se especifica). Si ninguno de los
    # dos campos se envia, el comportamiento es identico al de antes de este
    # issue: sin memoria, sin conversation_id en la respuesta.
    conversation_id: int | None = None
    mode: Literal["fast", "deliberation", "max_verification"] | None = None


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
    conversation_id: int | None = None
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
