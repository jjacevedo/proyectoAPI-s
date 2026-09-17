from sqlalchemy.ext.asyncio import AsyncSession

from app.core.orchestrator import DeliberationResult
from app.models.request_log import RequestLog


async def persist_request(session: AsyncSession, prompt: str, result: DeliberationResult) -> None:
    successful = [response for response in result.responses if response.succeeded]
    costs = [response.cost_estimated_usd for response in result.responses if response.cost_estimated_usd is not None]
    costs += [
        critique.response.cost_estimated_usd
        for critique in result.critiques
        if critique.response.cost_estimated_usd is not None
    ]
    log = RequestLog(
        prompt=prompt,
        models_used=[f"{response.provider}/{response.model}" for response in successful],
        individual_responses=[response.model_dump(exclude={"raw"}) for response in result.responses],
        critiques=[
            {
                "response": critique.response.model_dump(exclude={"raw"}),
                "reviewed_providers": critique.reviewed_providers,
            }
            for critique in result.critiques
        ],
        final_answer=result.final_answer,
        tokens=sum(response.tokens for response in result.responses)
        + sum(critique.response.tokens for critique in result.critiques),
        cost_usd=sum(costs) if costs else None,
        latency_ms=result.latency_ms,
        complexity=result.routing.complexity.value,
        disagreement_level=result.disagreement.level.value,
        disagreement_reason=result.disagreement.reason,
        disagreement_evidence=result.disagreement.evidence,
    )
    session.add(log)
    await session.commit()
