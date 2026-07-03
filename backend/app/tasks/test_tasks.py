import asyncio

from app.core.database import AsyncSessionLocal
from app.services.test_execution_service import test_execution_service
from app.services.test_generation_service import test_generation_service
from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, name="tests.generate")
def run_generate_tests_task(self, project_id: str, flow_ids: list[str] | None = None):
    async def _run():
        async with AsyncSessionLocal() as db:
            tests = await test_generation_service.generate_tests(db, project_id, flow_ids)
            return [t.id for t in tests]

    test_ids = asyncio.run(_run())
    return {"status": "completed", "test_ids": test_ids}


@celery_app.task(bind=True, name="tests.run")
def run_tests_task(self, project_id: str, test_ids: list[str] | None = None):
    async def _run():
        async with AsyncSessionLocal() as db:
            run = await test_execution_service.run_tests(db, project_id, test_ids)
            return run.id

    run_id = asyncio.run(_run())
    return {"status": "completed", "run_id": run_id}
