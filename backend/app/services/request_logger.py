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
    costs += [
        revision.cost_estimated_usd
        for revision in result.revisions
        if revision.cost_estimated_usd is not None
    ]
    if result.test_generation is not None and result.test_generation.cost_estimated_usd is not None:
        costs.append(result.test_generation.cost_estimated_usd)
    if result.solver_generation is not None and result.solver_generation.cost_estimated_usd is not None:
        costs.append(result.solver_generation.cost_estimated_usd)
    if result.fact_query_generation is not None and result.fact_query_generation.cost_estimated_usd is not None:
        costs.append(result.fact_query_generation.cost_estimated_usd)
    test_generation_tokens = result.test_generation.tokens if result.test_generation else 0
    solver_generation_tokens = result.solver_generation.tokens if result.solver_generation else 0
    fact_query_generation_tokens = result.fact_query_generation.tokens if result.fact_query_generation else 0

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
        revisions=[revision.model_dump(exclude={"raw"}) for revision in result.revisions],
        final_answer=result.final_answer,
        tokens=sum(response.tokens for response in result.responses)
        + sum(critique.response.tokens for critique in result.critiques)
        + sum(revision.tokens for revision in result.revisions)
        + test_generation_tokens
        + solver_generation_tokens
        + fact_query_generation_tokens,
        cost_usd=sum(costs) if costs else None,
        latency_ms=result.latency_ms,
        complexity=result.routing.complexity.value,
        disagreement_level=result.disagreement.level.value,
        disagreement_reason=result.disagreement.reason,
        disagreement_evidence=result.disagreement.evidence,
        task_type=result.routing.task_type.value,
        generated_tests=result.generated_tests,
        code_verifications=[verification.model_dump() for verification in result.code_verifications],
        reference_calculation=result.reference_calculation,
        calculation_verifications=[
            verification.model_dump() for verification in result.calculation_verifications
        ],
        fact_search_results=[result_item.model_dump() for result_item in result.fact_search_results],
    )
    session.add(log)
    await session.commit()
