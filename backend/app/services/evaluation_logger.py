from sqlalchemy.ext.asyncio import AsyncSession

from app.core.evaluator import EvaluationResult
from app.models.evaluation_log import EvaluationLog


async def persist_evaluation(session: AsyncSession, result: EvaluationResult) -> None:
    log = EvaluationLog(
        prompt=result.prompt,
        single_provider=result.single_provider,
        single_model=result.single_model,
        single_answer=result.single_answer,
        single_tokens=result.single_tokens,
        single_cost_usd=result.single_cost_estimated_usd,
        single_latency_ms=result.single_latency_ms,
        single_error=result.single_error,
        multi_answer=result.multi_answer,
        multi_tokens=result.multi_tokens,
        multi_cost_usd=result.multi_cost_estimated_usd,
        multi_latency_ms=result.multi_latency_ms,
        judge_verdict=result.judge_verdict,
        judge_reasoning=result.judge_reasoning,
        judge_error=result.judge_error,
    )
    session.add(log)
    await session.commit()
