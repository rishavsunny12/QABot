from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthenticatedUser, get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models import TeamRole
from app.services.access_service import access_service
from app.services.billing_service import billing_service

router = APIRouter(prefix="/billing", tags=["billing"])


class PlanLimitsResponse(BaseModel):
    test_runs: int | None = None
    crawl_pages: int | None = None
    ai_calls: int | None = None
    visual_comparisons: int | None = None
    projects: int | None = None


class BillingPlanResponse(BaseModel):
    slug: str
    name: str
    price_cents: int
    limits: PlanLimitsResponse


class MetricUsageResponse(BaseModel):
    used: int
    limit: int | None


class TeamBillingResponse(BaseModel):
    team_id: str
    plan: BillingPlanResponse
    period_start: datetime
    period_end: datetime
    usage: dict[str, MetricUsageResponse]


class ChangePlanRequest(BaseModel):
    plan_slug: str = Field(pattern="^(free|pro|enterprise)$")


async def _require_team_member(team_id: str, auth: AuthenticatedUser, db: AsyncSession):
    membership = await access_service.get_membership(db, auth.user.id, team_id)
    if not membership:
        raise HTTPException(status_code=403, detail="You do not have access to this team")
    return membership


@router.get("/plans", response_model=list[BillingPlanResponse])
async def list_plans(db: AsyncSession = Depends(get_db)):
    if not settings.billing_enabled:
        raise HTTPException(status_code=404, detail="Billing is not enabled in this deployment")
    from sqlalchemy import select

    from app.models import BillingPlan

    await billing_service.ensure_plans(db)
    plans = (await db.execute(select(BillingPlan).order_by(BillingPlan.price_cents))).scalars().all()
    return [
        BillingPlanResponse(
            slug=p.slug,
            name=p.name,
            price_cents=p.price_cents,
            limits=PlanLimitsResponse(**(p.limits_json or {})),
        )
        for p in plans
    ]


@router.get("/teams/{team_id}", response_model=TeamBillingResponse)
async def get_team_billing(
    team_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not settings.billing_enabled:
        raise HTTPException(status_code=404, detail="Billing is not enabled in this deployment")
    await _require_team_member(team_id, auth, db)
    await billing_service.ensure_plans(db)
    summary = await billing_service.get_usage_for_team(db, team_id)
    subscription = await billing_service.get_subscription(db, team_id)
    limits = subscription.plan.limits_json or {}
    return TeamBillingResponse(
        team_id=summary["team_id"],
        plan=BillingPlanResponse(
            slug=summary["plan"]["slug"],
            name=summary["plan"]["name"],
            price_cents=summary["plan"]["price_cents"],
            limits=PlanLimitsResponse(**limits),
        ),
        period_start=summary["period_start"],
        period_end=summary["period_end"],
        usage={
            metric: MetricUsageResponse(**values) for metric, values in summary["usage"].items()
        },
    )


@router.post("/teams/{team_id}/change-plan", response_model=TeamBillingResponse)
async def change_team_plan(
    team_id: str,
    payload: ChangePlanRequest,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not settings.billing_enabled:
        raise HTTPException(status_code=404, detail="Billing is not enabled in this deployment")
    membership = await _require_team_member(team_id, auth, db)
    if membership.role not in {TeamRole.OWNER.value, TeamRole.ADMIN.value}:
        raise HTTPException(status_code=403, detail="Requires admin role")

    try:
        await billing_service.change_plan(db, team_id, payload.plan_slug)
        await db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    summary = await billing_service.get_usage_for_team(db, team_id)
    subscription = await billing_service.get_subscription(db, team_id)
    limits = subscription.plan.limits_json or {}
    return TeamBillingResponse(
        team_id=summary["team_id"],
        plan=BillingPlanResponse(
            slug=summary["plan"]["slug"],
            name=summary["plan"]["name"],
            price_cents=summary["plan"]["price_cents"],
            limits=PlanLimitsResponse(**limits),
        ),
        period_start=summary["period_start"],
        period_end=summary["period_end"],
        usage={
            metric: MetricUsageResponse(**values) for metric, values in summary["usage"].items()
        },
    )


@router.post("/stripe/webhook")
async def stripe_webhook_stub():
    """Placeholder for Stripe billing webhooks (future integration)."""
    return {"status": "ignored", "message": "Stripe webhook handler not configured"}
