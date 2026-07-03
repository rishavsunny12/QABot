import asyncio

from celery import chord, group

from app.core.database import AsyncSessionLocal
from app.services.artifact_service import artifact_service
from app.services.test_execution_service import test_execution_service
from app.services.test_generation_service import test_generation_service
from app.tasks.celery_app import celery_app
from playwright_utils.executor import _execute_single_spec


def dispatch_farm_run(test_run, project, tests) -> None:
    run_dir = artifact_service.run_dir(test_run.id)
    run_dir.mkdir(parents=True, exist_ok=True)
    signatures = []
    for index, test in enumerate(tests):
        spec_path = str(artifact_service.resolve_path(test.file_path))
        signatures.append(
            run_single_test_task.s(
                test_run.id,
                test.id,
                spec_path,
                project.base_url,
                index,
            )
        )
    chord(group(signatures))(finalize_run_task.s(test_run.id))


@celery_app.task(bind=True, name="tests.generate")
def run_generate_tests_task(self, project_id: str, flow_ids: list[str] | None = None):
    async def _run():
        async with AsyncSessionLocal() as db:
            tests = await test_generation_service.generate_tests(db, project_id, flow_ids)
            return [t.id for t in tests]

    test_ids = asyncio.run(_run())
    return {"status": "completed", "test_ids": test_ids}


@celery_app.task(bind=True, name="tests.run_single")
def run_single_test_task(
    self,
    run_id: str,
    test_id: str,
    spec_path: str,
    base_url: str,
    output_index: int,
):
    run_dir = artifact_service.run_dir(run_id)
    result = _execute_single_spec(spec_path, run_dir, base_url, index=output_index)
    result["test_id"] = test_id
    return result


@celery_app.task(bind=True, name="tests.finalize_run")
def finalize_run_task(self, results: list, run_id: str):
    async def _run():
        async with AsyncSessionLocal() as db:
            await test_execution_service.finalize_farm_run(db, run_id, results)

    asyncio.run(_run())
    return {"status": "completed", "run_id": run_id}


@celery_app.task(bind=True, name="tests.run")
def run_tests_task(self, project_id: str, test_ids: list[str] | None = None):
    async def _prepare():
        async with AsyncSessionLocal() as db:
            return await test_execution_service.prepare_run(db, project_id, test_ids)

    test_run, project, tests = asyncio.run(_prepare())

    if test_run.execution_mode == "farm":
        dispatch_farm_run(test_run, project, tests)
        return {"status": "queued", "run_id": test_run.id, "execution_mode": "farm"}

    async def _run_local():
        async with AsyncSessionLocal() as db:
            run = await test_execution_service.run_tests_local(db, test_run, project, tests)
            return run.id

    run_id = asyncio.run(_run_local())
    return {"status": "completed", "run_id": run_id, "execution_mode": "local"}
