import asyncio

from app.core.database import AsyncSessionLocal
from app.services.visual_regression_service import visual_regression_service
from app.tasks.celery_app import celery_app


@celery_app.task(name="visual.run_comparison")
def run_visual_comparison_task(project_id: str, threshold_percent: float = 1.0):
    async def _run():
        async with AsyncSessionLocal() as db:
            run = await visual_regression_service.run_comparison(
                db, project_id, threshold_percent=threshold_percent
            )
            return run.id

    run_id = asyncio.run(_run())
    return {"status": "completed", "run_id": run_id}
