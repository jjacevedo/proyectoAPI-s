from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import settings
from app.core.rate_limiter import RateLimiter
from app.services.budget_service import get_spent_today_usd

# Un unico limitador compartido por /api/chat y /api/evaluate: ambos son los
# endpoints "caros" (llaman LLMs reales), asi que comparten el mismo cupo por
# minuto en vez de tener uno independiente cada uno.
_shared_rate_limiter = RateLimiter(max_requests=settings.rate_limit_requests_per_minute)


def get_rate_limiter() -> RateLimiter:
    return _shared_rate_limiter


async def enforce_rate_limit(request: Request, limiter: RateLimiter = Depends(get_rate_limiter)) -> None:
    if not settings.enable_rate_limiting:
        return
    client_key = request.client.host if request.client else "unknown"
    if not limiter.allow(client_key):
        raise HTTPException(
            status_code=429,
            detail="Se alcanzó el límite de solicitudes por minuto. Intenta de nuevo en unos segundos.",
        )


async def enforce_daily_budget(db: AsyncSession = Depends(get_db)) -> None:
    if settings.daily_budget_usd is None:
        return
    spent = await get_spent_today_usd(db)
    if spent >= settings.daily_budget_usd:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Presupuesto diario de ${settings.daily_budget_usd:.2f} alcanzado "
                f"(gastado ${spent:.4f} hoy)."
            ),
        )
