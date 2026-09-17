from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import settings
from app.core.orchestrator import AllProvidersFailedError, DeliberationOrchestrator
from app.providers.registry import build_providers
from app.schemas.chat import ChatRequest, ChatResponse, ProviderResponse
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
    costs = [item.cost_estimated_usd for item in response_models if item.cost_estimated_usd is not None]
    return ChatResponse(
        final_answer=result.final_answer,
        responses=response_models,
        models_used=[f"{item.provider}/{item.model}" for item in response_models if item.error is None],
        total_tokens=sum(item.tokens for item in response_models),
        total_cost_estimated_usd=sum(costs) if costs else None,
        latency_ms=result.latency_ms,
    )
