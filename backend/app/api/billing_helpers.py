from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.billing_service import QuotaExceededError, billing_service


async def enforce_team_quota(
    db: AsyncSession,
    team_id: str | None,
    metric: str,
    quantity: int = 1,
) -> None:
    if not settings.billing_enabled:
        return
    if not team_id:
        return
    try:
        await billing_service.check_quota(db, team_id, metric, quantity)
    except QuotaExceededError as exc:
        raise HTTPException(
            status_code=402,
            detail={
                "message": str(exc),
                "metric": exc.metric,
                "limit": exc.limit,
                "used": exc.used,
            },
        ) from exc


async def record_team_usage(
    db: AsyncSession,
    team_id: str | None,
    metric: str,
    quantity: int = 1,
    project_id: str | None = None,
) -> None:
    if not settings.billing_enabled:
        return
    if not team_id:
        return
    await billing_service.record_usage(db, team_id, metric, quantity, project_id)
