import asyncio

from app.core.database import AsyncSessionLocal
from app.services.schedule_service import schedule_service
from app.tasks.celery_app import celery_app


@celery_app.task(name="schedules.check_due")
def check_due_schedules_task():
    async def _run():
        async with AsyncSessionLocal() as db:
            return await schedule_service.process_due_schedules(db)

    run_ids = asyncio.run(_run())
    return {"triggered_runs": run_ids, "count": len(run_ids)}
