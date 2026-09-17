from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation_log import EvaluationLog
from app.models.request_log import RequestLog


def _start_of_today_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


async def get_spent_today_usd(session: AsyncSession) -> float:
    """Suma el costo estimado de todo lo persistido hoy (UTC) en
    request_logs y evaluation_logs. Se calcula sobre datos reales ya
    guardados en vez de un contador en memoria, para que el limite de
    presupuesto sea correcto incluso si el proceso se reinicia."""
    start = _start_of_today_utc()

    request_total = (
        await session.execute(
            select(func.coalesce(func.sum(RequestLog.cost_usd), 0.0)).where(RequestLog.created_at >= start)
        )
    ).scalar_one()

    single_total, multi_total = (
        await session.execute(
            select(
                func.coalesce(func.sum(EvaluationLog.single_cost_usd), 0.0),
                func.coalesce(func.sum(EvaluationLog.multi_cost_usd), 0.0),
            ).where(EvaluationLog.created_at >= start)
        )
    ).one()

    return float(request_total) + float(single_total) + float(multi_total)
