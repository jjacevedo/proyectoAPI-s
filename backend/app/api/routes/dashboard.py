from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.evaluation_log import EvaluationLog
from app.models.request_log import RequestLog
from app.schemas.dashboard import DashboardStats
from app.services.dashboard_stats import compute_dashboard_stats

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)) -> DashboardStats:
    request_logs = list((await db.execute(select(RequestLog))).scalars().all())
    evaluation_logs = list((await db.execute(select(EvaluationLog))).scalars().all())
    return compute_dashboard_stats(request_logs, evaluation_logs)
