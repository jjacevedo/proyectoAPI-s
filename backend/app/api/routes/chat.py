from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import settings
from app.core.orchestrator import AllProvidersFailedError, DeliberationOrchestrator
from app.providers.registry import build_providers
from app.schemas.chat import ChatRequest, ChatResponse, CritiqueResponse, ProviderResponse
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
    costs = [item.cost_estimated_usd for item in response_models if item.cost_estimated_usd is not None]
    costs += [item.cost_estimated_usd for item in critique_models if item.cost_estimated_usd is not None]
    return ChatResponse(
        final_answer=result.final_answer,
        responses=response_models,
        critiques=critique_models,
        models_used=[f"{item.provider}/{item.model}" for item in response_models if item.error is None],
        total_tokens=sum(item.tokens for item in response_models) + sum(item.tokens for item in critique_models),
        total_cost_estimated_usd=sum(costs) if costs else None,
        latency_ms=result.latency_ms,
        complexity=result.routing.complexity.value,
        routing_reason=result.routing.reason,
        disagreement_level=result.disagreement.level.value,
        disagreement_reason=result.disagreement.reason,
        disagreement_evidence=result.disagreement.evidence,
    )
