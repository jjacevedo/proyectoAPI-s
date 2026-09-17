from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import settings
from app.core.orchestrator import AllProvidersFailedError, DeliberationOrchestrator
from app.providers.registry import build_providers
from app.schemas.chat import (
    CalculationVerificationResponse,
    ChatRequest,
    ChatResponse,
    CodeVerificationResponse,
    CritiqueResponse,
    ProviderResponse,
)
from app.services.request_logger import persist_request

router = APIRouter(tags=["chat"])


def get_orchestrator() -> DeliberationOrchestrator:
    return DeliberationOrchestrator(build_providers(settings), settings)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    orchestrator: DeliberationOrchestrator = Depends(get_orchestrator),
) -> ChatResponse:
    if len(request.prompt) > settings.max_prompt_chars:
        raise HTTPException(status_code=413, detail="Prompt exceeds the configured character limit")
    try:
        result = await orchestrator.run(request.prompt)
    except AllProvidersFailedError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    await persist_request(db, request.prompt, result)
    response_models = [
        ProviderResponse(
            provider=response.provider,
            model=response.model,
            content=response.content,
            tokens=response.tokens,
            latency_ms=response.latency_ms,
            cost_estimated_usd=response.cost_estimated_usd,
            error=response.error,
        )
        for response in result.responses
    ]
    critique_models = [
        CritiqueResponse(
            provider=critique.response.provider,
            model=critique.response.model,
            content=critique.response.content,
            reviewed_providers=critique.reviewed_providers,
            tokens=critique.response.tokens,
            latency_ms=critique.response.latency_ms,
            cost_estimated_usd=critique.response.cost_estimated_usd,
            error=critique.response.error,
        )
        for critique in result.critiques
    ]
    revision_models = [
        ProviderResponse(
            provider=revision.provider,
            model=revision.model,
            content=revision.content,
            tokens=revision.tokens,
            latency_ms=revision.latency_ms,
            cost_estimated_usd=revision.cost_estimated_usd,
            error=revision.error,
        )
        for revision in result.revisions
    ]
    code_verification_models = [
        CodeVerificationResponse(
            provider=verification.provider,
            model=verification.model,
            passed=verification.passed,
            tests_run=verification.tests_run,
            tests_passed=verification.tests_passed,
            tests_failed=verification.tests_failed,
            stdout=verification.stdout,
            stderr=verification.stderr,
            error=verification.error,
            timed_out=verification.timed_out,
        )
        for verification in result.code_verifications
    ]
    calculation_verification_models = [
        CalculationVerificationResponse(
            provider=verification.provider,
            model=verification.model,
            passed=verification.passed,
            candidate_value=verification.candidate_value,
            reference_value=verification.reference_value,
            difference=verification.difference,
            error=verification.error,
            timed_out=verification.timed_out,
        )
        for verification in result.calculation_verifications
    ]
    test_generation_tokens = result.test_generation.tokens if result.test_generation else 0
    test_generation_cost = result.test_generation.cost_estimated_usd if result.test_generation else None
    solver_generation_tokens = result.solver_generation.tokens if result.solver_generation else 0
    solver_generation_cost = result.solver_generation.cost_estimated_usd if result.solver_generation else None

    costs = [item.cost_estimated_usd for item in response_models if item.cost_estimated_usd is not None]
    costs += [item.cost_estimated_usd for item in critique_models if item.cost_estimated_usd is not None]
    costs += [item.cost_estimated_usd for item in revision_models if item.cost_estimated_usd is not None]
    if test_generation_cost is not None:
        costs.append(test_generation_cost)
    if solver_generation_cost is not None:
        costs.append(solver_generation_cost)
    return ChatResponse(
        final_answer=result.final_answer,
        responses=response_models,
        critiques=critique_models,
        revisions=revision_models,
        models_used=[f"{item.provider}/{item.model}" for item in response_models if item.error is None],
        total_tokens=sum(item.tokens for item in response_models)
        + sum(item.tokens for item in critique_models)
        + sum(item.tokens for item in revision_models)
        + test_generation_tokens
        + solver_generation_tokens,
        total_cost_estimated_usd=sum(costs) if costs else None,
        latency_ms=result.latency_ms,
        complexity=result.routing.complexity.value,
        routing_reason=result.routing.reason,
        task_type=result.routing.task_type.value,
        disagreement_level=result.disagreement.level.value,
        disagreement_reason=result.disagreement.reason,
        disagreement_evidence=result.disagreement.evidence,
        generated_tests=result.generated_tests,
        code_verifications=code_verification_models,
        reference_calculation=result.reference_calculation,
        calculation_verifications=calculation_verification_models,
    )
