from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import get_logger
from app.models import BillingPlan, Project, TeamSubscription, UsageEvent

logger = get_logger("BillingService")

DEFAULT_PLANS: list[dict[str, Any]] = [
    {
        "slug": "free",
        "name": "Free",
        "price_cents": 0,
        "limits_json": {
            "test_runs": 50,
            "crawl_pages": 100,
            "ai_calls": 25,
            "visual_comparisons": 10,
            "projects": 3,
        },
    },
    {
        "slug": "pro",
        "name": "Pro",
        "price_cents": 4900,
        "limits_json": {
            "test_runs": 500,
            "crawl_pages": 1000,
            "ai_calls": 250,
            "visual_comparisons": 100,
            "projects": 15,
        },
    },
    {
        "slug": "enterprise",
        "name": "Enterprise",
        "price_cents": 0,
        "limits_json": {
            "test_runs": -1,
            "crawl_pages": -1,
            "ai_calls": -1,
            "visual_comparisons": -1,
            "projects": -1,
        },
    },
]

METRICS = ("test_runs", "crawl_pages", "ai_calls", "visual_comparisons", "projects")


class QuotaExceededError(Exception):
    def __init__(self, metric: str, limit: int, used: int):
        self.metric = metric
        self.limit = limit
        self.used = used
        super().__init__(f"Quota exceeded for {metric}: {used}/{limit}")


class BillingService:
    """Track team usage and enforce plan limits."""

    def current_period(self) -> tuple[datetime, datetime]:
        now = datetime.now(timezone.utc)
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        return start, end

    async def ensure_plans(self, db: AsyncSession) -> None:
        for plan_data in DEFAULT_PLANS:
            existing = (
                await db.execute(select(BillingPlan).where(BillingPlan.slug == plan_data["slug"]))
            ).scalar_one_or_none()
            if existing:
                existing.name = plan_data["name"]
                existing.price_cents = plan_data["price_cents"]
                existing.limits_json = plan_data["limits_json"]
            else:
                db.add(BillingPlan(**plan_data))
        await db.commit()

    async def get_plan_by_slug(self, db: AsyncSession, slug: str) -> BillingPlan:
        plan = (
            await db.execute(select(BillingPlan).where(BillingPlan.slug == slug))
        ).scalar_one_or_none()
        if not plan:
            raise ValueError(f"Plan {slug} not found")
        return plan

    async def ensure_team_subscription(self, db: AsyncSession, team_id: str) -> TeamSubscription:
        existing = (
            await db.execute(
                select(TeamSubscription)
                .options(selectinload(TeamSubscription.plan))
                .where(TeamSubscription.team_id == team_id)
            )
        ).scalar_one_or_none()
        if existing:
            return existing

        free_plan = await self.get_plan_by_slug(db, "free")
        period_start, period_end = self.current_period()
        subscription = TeamSubscription(
            team_id=team_id,
            plan_id=free_plan.id,
            status="active",
            current_period_start=period_start,
            current_period_end=period_end,
        )
        db.add(subscription)
        await db.flush()
        logger.log("subscription_created", "Assigned free plan", team_id=team_id)
        return subscription

    async def get_subscription(self, db: AsyncSession, team_id: str) -> TeamSubscription:
        subscription = await self.ensure_team_subscription(db, team_id)
        if not subscription.plan:
            await db.refresh(subscription, attribute_names=["plan"])
        return subscription

    async def count_projects(self, db: AsyncSession, team_id: str) -> int:
        result = await db.execute(
            select(func.count(Project.id)).where(Project.team_id == team_id)
        )
        return int(result.scalar_one())

    async def sum_metric_usage(
        self, db: AsyncSession, team_id: str, metric: str, period_start: datetime, period_end: datetime
    ) -> int:
        if metric == "projects":
            return await self.count_projects(db, team_id)
        result = await db.execute(
            select(func.coalesce(func.sum(UsageEvent.quantity), 0)).where(
                UsageEvent.team_id == team_id,
                UsageEvent.metric == metric,
                UsageEvent.recorded_at >= period_start,
                UsageEvent.recorded_at < period_end,
            )
        )
        return int(result.scalar_one())

    async def get_usage_for_team(self, db: AsyncSession, team_id: str) -> dict[str, Any]:
        subscription = await self.get_subscription(db, team_id)
        period_start = subscription.current_period_start
        period_end = subscription.current_period_end
        limits = subscription.plan.limits_json or {}

        usage: dict[str, dict[str, int | None]] = {}
        for metric in METRICS:
            used = await self.sum_metric_usage(db, team_id, metric, period_start, period_end)
            limit = limits.get(metric, 0)
            usage[metric] = {
                "used": used,
                "limit": None if limit == -1 else int(limit),
            }

        return {
            "team_id": team_id,
            "plan": {
                "slug": subscription.plan.slug,
                "name": subscription.plan.name,
                "price_cents": subscription.plan.price_cents,
            },
            "period_start": period_start,
            "period_end": period_end,
            "usage": usage,
        }

    async def check_quota(
        self, db: AsyncSession, team_id: str, metric: str, quantity: int = 1
    ) -> None:
        if not settings.billing_enforcement:
            return

        subscription = await self.get_subscription(db, team_id)
        limits = subscription.plan.limits_json or {}
        limit = limits.get(metric)
        if limit is None or limit == -1:
            return

        used = await self.sum_metric_usage(
            db,
            team_id,
            metric,
            subscription.current_period_start,
            subscription.current_period_end,
        )
        if metric != "projects":
            projected = used + quantity
        else:
            projected = used + quantity

        if projected > int(limit):
            raise QuotaExceededError(metric, int(limit), used)

    async def record_usage(
        self,
        db: AsyncSession,
        team_id: str,
        metric: str,
        quantity: int = 1,
        project_id: str | None = None,
    ) -> None:
        if quantity <= 0:
            return
        event = UsageEvent(
            team_id=team_id,
            metric=metric,
            quantity=quantity,
            project_id=project_id,
        )
        db.add(event)
        await db.flush()
        logger.log(
            "usage_recorded",
            f"{metric} +{quantity}",
            team_id=team_id,
            project_id=project_id,
        )

    async def change_plan(self, db: AsyncSession, team_id: str, plan_slug: str) -> TeamSubscription:
        plan = await self.get_plan_by_slug(db, plan_slug)
        subscription = await self.get_subscription(db, team_id)
        subscription.plan_id = plan.id
        subscription.status = "active"
        period_start, period_end = self.current_period()
        subscription.current_period_start = period_start
        subscription.current_period_end = period_end
        subscription.updated_at = datetime.now(timezone.utc)
        await db.flush()
        logger.log("plan_changed", f"Team moved to {plan_slug}", team_id=team_id)
        return subscription


billing_service = BillingService()
