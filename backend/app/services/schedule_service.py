from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import TestSchedule
from app.services.test_execution_service import test_execution_service

logger = get_logger("ScheduleService")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def compute_next_run(interval_minutes: int, from_time: datetime | None = None) -> datetime:
    base = from_time or _utcnow()
    return base + timedelta(minutes=interval_minutes)


class ScheduleService:
    """Manage recurring test run schedules."""

    async def create(
        self,
        db: AsyncSession,
        project_id: str,
        name: str,
        interval_minutes: int,
        test_ids: list[str] | None = None,
        enabled: bool = True,
    ) -> TestSchedule:
        now = _utcnow()
        schedule = TestSchedule(
            project_id=project_id,
            name=name,
            interval_minutes=interval_minutes,
            test_ids_json=test_ids,
            enabled=enabled,
            next_run_at=compute_next_run(interval_minutes, now) if enabled else None,
        )
        db.add(schedule)
        await db.flush()
        logger.log("schedule_created", f"Created schedule {name}", project_id=project_id)
        return schedule

    async def list_for_project(self, db: AsyncSession, project_id: str) -> list[TestSchedule]:
        result = await db.execute(
            select(TestSchedule)
            .where(TestSchedule.project_id == project_id)
            .order_by(TestSchedule.created_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, db: AsyncSession, schedule_id: str) -> TestSchedule | None:
        return (
            await db.execute(select(TestSchedule).where(TestSchedule.id == schedule_id))
        ).scalar_one_or_none()

    async def update(
        self,
        db: AsyncSession,
        schedule: TestSchedule,
        *,
        name: str | None = None,
        interval_minutes: int | None = None,
        test_ids: list[str] | None = None,
        enabled: bool | None = None,
    ) -> TestSchedule:
        if name is not None:
            schedule.name = name
        if interval_minutes is not None:
            schedule.interval_minutes = interval_minutes
            if schedule.enabled:
                schedule.next_run_at = compute_next_run(
                    schedule.interval_minutes, schedule.last_run_at or _utcnow()
                )
        if test_ids is not None:
            schedule.test_ids_json = test_ids
        if enabled is not None:
            schedule.enabled = enabled
            if enabled and schedule.next_run_at is None:
                schedule.next_run_at = compute_next_run(
                    schedule.interval_minutes, schedule.last_run_at or _utcnow()
                )
            if not enabled:
                schedule.next_run_at = None
        schedule.updated_at = _utcnow()
        await db.flush()
        return schedule

    async def delete(self, db: AsyncSession, schedule: TestSchedule) -> None:
        await db.delete(schedule)
        await db.flush()

    async def process_due_schedules(self, db: AsyncSession) -> list[str]:
        """Run all schedules that are due and return triggered run IDs."""
        now = _utcnow()
        result = await db.execute(
            select(TestSchedule).where(
                TestSchedule.enabled.is_(True),
                TestSchedule.next_run_at.is_not(None),
                TestSchedule.next_run_at <= now,
            )
        )
        schedules = result.scalars().all()
        run_ids: list[str] = []

        for schedule in schedules:
            try:
                test_run = await test_execution_service.run_tests(
                    db,
                    schedule.project_id,
                    test_ids=schedule.test_ids_json,
                    triggered_by=f"schedule:{schedule.id}",
                    run_type="scheduled",
                )
                schedule.last_run_at = now
                schedule.next_run_at = compute_next_run(schedule.interval_minutes, now)
                schedule.updated_at = now
                await db.flush()
                run_ids.append(test_run.id)
                logger.log(
                    "schedule_triggered",
                    f"Schedule {schedule.name} triggered run {test_run.id}",
                    project_id=schedule.project_id,
                )
            except ValueError as exc:
                logger.log(
                    "schedule_skipped",
                    f"Schedule {schedule.name} skipped: {exc}",
                    project_id=schedule.project_id,
                )
                schedule.next_run_at = compute_next_run(schedule.interval_minutes, now)

        if schedules:
            await db.commit()
        return run_ids


schedule_service = ScheduleService()
