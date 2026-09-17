from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import settings
from app.core.orchestrator import AllProvidersFailedError, DeliberationOrchestrator
from app.core.router import TaskComplexity, TaskRouter
from app.providers.registry import build_providers
from app.schemas.chat import (
    CalculationVerificationResponse,
    ChatRequest,
    ChatResponse,
    CodeVerificationResponse,
    CritiqueResponse,
    FactCheckResultResponse,
    ProviderResponse,
)
from app.services.conversation_service import (
    append_message,
    build_contextual_prompt,
    create_conversation,
    get_conversation,
    get_recent_messages,
)
from app.services.request_logger import persist_request

router = APIRouter(tags=["chat"])

# "fast" salta la critica cruzada/reevaluacion y fuerza 1 solo provider;
# "max_verification" fuerza 3 providers y activa toda la deliberacion y
# verificacion externa disponible, sin importar el largo/tipo del prompt.
_MODE_SETTINGS_OVERRIDES = {
    "fast": {"enable_cross_critique": False, "enable_reevaluation_round": False},
    "max_verification": {
        "enable_cross_critique": True,
        "enable_reevaluation_round": True,
        "enable_code_verification": True,
        "enable_calculation_verification": True,
        "enable_fact_search": True,
    },
}
_MODE_FORCED_COMPLEXITY = {
    "fast": TaskComplexity.LOW,
    "max_verification": TaskComplexity.HIGH,
}


def get_orchestrator() -> DeliberationOrchestrator:
    return DeliberationOrchestrator(build_providers(settings), settings)


def _build_orchestrator_for_mode(mode: str) -> DeliberationOrchestrator:
    overrides = _MODE_SETTINGS_OVERRIDES.get(mode)
    mode_settings = settings.model_copy(update=overrides) if overrides else settings
    router_override = TaskRouter(forced_complexity=_MODE_FORCED_COMPLEXITY.get(mode))
    return DeliberationOrchestrator(build_providers(mode_settings), mode_settings, router=router_override)


def get_mode_orchestrator_builder():
    """Fabrica de orchestrators para modos != 'deliberation' (issue #16),
    inyectable igual que get_orchestrator para poder sustituirla en tests
    sin necesitar providers reales configurados."""
    return _build_orchestrator_for_mode


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    orchestrator: DeliberationOrchestrator = Depends(get_orchestrator),
    mode_orchestrator_builder=Depends(get_mode_orchestrator_builder),
) -> ChatResponse:
    if len(request.prompt) > settings.max_prompt_chars:
        raise HTTPException(status_code=413, detail="Prompt exceeds the configured character limit")

    conversation_id: int | None = None
    active_orchestrator = orchestrator
    prompt_for_providers = request.prompt

    # Memoria de conversaciones (issue #16) es opt-in: si ni conversation_id
    # ni mode se envian, el comportamiento es identico al de /api/chat antes
    # de este issue (sin tocar la base de datos de conversaciones/mensajes).
    if request.conversation_id is not None or request.mode is not None:
        if request.conversation_id is not None:
            conversation = await get_conversation(db, request.conversation_id)
            if conversation is None:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            conversation = await create_conversation(db, request.mode or "deliberation")

        history = await get_recent_messages(db, conversation.id, settings.conversation_history_max_messages)
        prompt_for_providers = build_contextual_prompt(history, request.prompt)
        if conversation.mode != "deliberation":
            active_orchestrator = mode_orchestrator_builder(conversation.mode)
        conversation_id = conversation.id

    try:
        result = await active_orchestrator.run(prompt_for_providers)
    except AllProvidersFailedError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if conversation_id is not None:
        await append_message(db, conversation_id, "user", request.prompt)
        await append_message(db, conversation_id, "assistant", result.final_answer)

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
    fact_search_result_models = [
        FactCheckResultResponse(
            query=result_item.query,
            title=result_item.title,
            extract=result_item.extract,
            url=result_item.url,
            error=result_item.error,
        )
        for result_item in result.fact_search_results
    ]
    test_generation_tokens = result.test_generation.tokens if result.test_generation else 0
    test_generation_cost = result.test_generation.cost_estimated_usd if result.test_generation else None
    solver_generation_tokens = result.solver_generation.tokens if result.solver_generation else 0
    solver_generation_cost = result.solver_generation.cost_estimated_usd if result.solver_generation else None
    fact_query_generation_tokens = result.fact_query_generation.tokens if result.fact_query_generation else 0
    fact_query_generation_cost = (
        result.fact_query_generation.cost_estimated_usd if result.fact_query_generation else None
    )

    costs = [item.cost_estimated_usd for item in response_models if item.cost_estimated_usd is not None]
    costs += [item.cost_estimated_usd for item in critique_models if item.cost_estimated_usd is not None]
    costs += [item.cost_estimated_usd for item in revision_models if item.cost_estimated_usd is not None]
    if test_generation_cost is not None:
        costs.append(test_generation_cost)
    if solver_generation_cost is not None:
        costs.append(solver_generation_cost)
    if fact_query_generation_cost is not None:
        costs.append(fact_query_generation_cost)
    return ChatResponse(
        conversation_id=conversation_id,
        final_answer=result.final_answer,
        responses=response_models,
        critiques=critique_models,
        revisions=revision_models,
        models_used=[f"{item.provider}/{item.model}" for item in response_models if item.error is None],
        total_tokens=sum(item.tokens for item in response_models)
        + sum(item.tokens for item in critique_models)
        + sum(item.tokens for item in revision_models)
        + test_generation_tokens
        + solver_generation_tokens
        + fact_query_generation_tokens,
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
        fact_search_results=fact_search_result_models,
    )
