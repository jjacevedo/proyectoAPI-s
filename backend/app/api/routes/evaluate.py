from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.rate_limit_deps import enforce_daily_budget, enforce_rate_limit
from app.config import settings
from app.core.evaluator import EvaluationJudge, EvaluationResult, SingleLLMBaseline, extract_verdict
from app.core.orchestrator import AllProvidersFailedError, DeliberationOrchestrator, DeliberationResult
from app.providers.registry import build_providers
from app.schemas.evaluate import EvaluateRequest, EvaluateResponse
from app.services.evaluation_logger import persist_evaluation

router = APIRouter(tags=["evaluate"])


def get_orchestrator() -> DeliberationOrchestrator:
    return DeliberationOrchestrator(build_providers(settings), settings)


def _deliberation_totals(result: DeliberationResult) -> tuple[int, float | None]:
    """Mismo calculo que /api/chat (ver api/routes/chat.py) para que la
    comparacion de costo/tokens contra el baseline de un solo LLM sea justa
    y consistente con lo que el usuario ve en /api/chat."""
    costs = [response.cost_estimated_usd for response in result.responses if response.cost_estimated_usd is not None]
    costs += [
        critique.response.cost_estimated_usd
        for critique in result.critiques
        if critique.response.cost_estimated_usd is not None
    ]
    costs += [
        revision.cost_estimated_usd for revision in result.revisions if revision.cost_estimated_usd is not None
    ]
    extra_tokens = 0
    for extra in (result.test_generation, result.solver_generation, result.fact_query_generation):
        if extra is not None:
            extra_tokens += extra.tokens
            if extra.cost_estimated_usd is not None:
                costs.append(extra.cost_estimated_usd)

    total_tokens = (
        sum(response.tokens for response in result.responses)
        + sum(critique.response.tokens for critique in result.critiques)
        + sum(revision.tokens for revision in result.revisions)
        + extra_tokens
    )
    return total_tokens, sum(costs) if costs else None


@router.post(
    "/evaluate",
    response_model=EvaluateResponse,
    dependencies=[Depends(enforce_rate_limit), Depends(enforce_daily_budget)],
)
async def evaluate(
    request: EvaluateRequest,
    db: AsyncSession = Depends(get_db),
    orchestrator: DeliberationOrchestrator = Depends(get_orchestrator),
) -> EvaluateResponse:
    if len(request.prompt) > settings.max_prompt_chars:
        raise HTTPException(status_code=413, detail="Prompt exceeds the configured character limit")

    providers = orchestrator.providers
    if not providers:
        raise HTTPException(status_code=502, detail="No LLM providers are configured")

    baseline_provider = providers.get(settings.synthesizer_provider) or next(iter(providers.values()))
    single_response = await SingleLLMBaseline().run(
        baseline_provider, request.prompt, max_tokens=settings.max_tokens_per_request
    )

    try:
        multi_result = await orchestrator.run(request.prompt)
    except AllProvidersFailedError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    multi_tokens, multi_cost = _deliberation_totals(multi_result)

    judge_verdict: str | None = None
    judge_reasoning: str | None = None
    judge_error: str | None = None
    if settings.enable_evaluation_judge and single_response.succeeded:
        judge_provider = (
            providers.get(settings.evaluation_judge_provider or settings.synthesizer_provider) or baseline_provider
        )
        judge_response = await EvaluationJudge(settings.max_tokens_per_request).run(
            judge_provider, request.prompt, single_response.content or "", multi_result.final_answer
        )
        if judge_response.succeeded:
            judge_verdict, judge_reasoning = extract_verdict(judge_response.content)
        else:
            judge_error = judge_response.error

    result = EvaluationResult(
        prompt=request.prompt,
        single_answer=single_response.content,
        single_provider=single_response.provider,
        single_model=single_response.model,
        single_tokens=single_response.tokens,
        single_cost_estimated_usd=single_response.cost_estimated_usd,
        single_latency_ms=single_response.latency_ms,
        single_error=single_response.error,
        multi_answer=multi_result.final_answer,
        multi_tokens=multi_tokens,
        multi_cost_estimated_usd=multi_cost,
        multi_latency_ms=multi_result.latency_ms,
        judge_verdict=judge_verdict,
        judge_reasoning=judge_reasoning,
        judge_error=judge_error,
    )
    await persist_evaluation(db, result)

    cost_delta = None
    if result.single_cost_estimated_usd is not None and result.multi_cost_estimated_usd is not None:
        cost_delta = result.multi_cost_estimated_usd - result.single_cost_estimated_usd

    return EvaluateResponse(
        prompt=result.prompt,
        single_answer=result.single_answer,
        single_provider=result.single_provider,
        single_model=result.single_model,
        single_tokens=result.single_tokens,
        single_cost_estimated_usd=result.single_cost_estimated_usd,
        single_latency_ms=result.single_latency_ms,
        single_error=result.single_error,
        multi_answer=result.multi_answer,
        multi_tokens=result.multi_tokens,
        multi_cost_estimated_usd=result.multi_cost_estimated_usd,
        multi_latency_ms=result.multi_latency_ms,
        token_delta=result.multi_tokens - result.single_tokens,
        cost_delta_usd=cost_delta,
        latency_delta_ms=result.multi_latency_ms - result.single_latency_ms,
        judge_verdict=result.judge_verdict,
        judge_reasoning=result.judge_reasoning,
        judge_error=result.judge_error,
    )
