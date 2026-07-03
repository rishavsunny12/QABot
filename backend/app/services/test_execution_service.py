from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.billing_helpers import enforce_team_quota, record_team_usage
from app.core.config import settings
from app.core.logging import get_logger
from app.models import GeneratedTest, Project, TestRun, TestRunResult
from app.services.artifact_service import artifact_service
from app.services.failure_analysis_service import failure_analysis_service
from app.services.selector_healing_service import selector_healing_service
from playwright_utils.executor import execute_specs

logger = get_logger("TestExecutionService")


class TestExecutionService:
    """Queue and execute Playwright tests locally or across a Celery worker farm."""

    def resolve_parallel_workers(self, project: Project) -> int:
        workers = project.parallel_workers or settings.default_parallel_workers
        return max(1, min(workers, settings.max_parallel_workers))

    def resolve_execution_mode(self, project: Project) -> str:
        mode = project.execution_mode or "local"
        return mode if mode in {"local", "farm"} else "local"

    async def prepare_run(
        self,
        db: AsyncSession,
        project_id: str,
        test_ids: list[str] | None = None,
        triggered_by: str = "user",
        run_type: str = "manual",
    ) -> tuple[TestRun, Project, list[GeneratedTest]]:
        query = select(GeneratedTest).where(GeneratedTest.project_id == project_id)
        if test_ids:
            query = query.where(GeneratedTest.id.in_(test_ids))
        tests = (await db.execute(query)).scalars().all()
        if not tests:
            raise ValueError("No tests found to run")

        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one()
        await enforce_team_quota(db, project.team_id, "test_runs", quantity=1)
        parallel_workers = self.resolve_parallel_workers(project)
        execution_mode = self.resolve_execution_mode(project)

        test_run = TestRun(
            project_id=project_id,
            run_type=run_type,
            status="running",
            started_at=datetime.now(timezone.utc),
            triggered_by=triggered_by,
            parallel_workers=parallel_workers,
            execution_mode=execution_mode,
        )
        db.add(test_run)
        await db.flush()
        await record_team_usage(db, project.team_id, "test_runs", quantity=1, project_id=project_id)
        await db.commit()
        return test_run, project, list(tests)

    async def run_tests_local(
        self,
        db: AsyncSession,
        test_run: TestRun,
        project: Project,
        tests: list[GeneratedTest],
    ) -> TestRun:
        run_dir = artifact_service.run_dir(test_run.id)
        spec_paths = [str(artifact_service.resolve_path(t.file_path)) for t in tests]
        workers = test_run.parallel_workers or 1
        results = execute_specs(
            spec_paths,
            run_dir,
            base_url=project.base_url,
            max_workers=workers,
        )
        await self._persist_results(db, test_run, tests, results)
        return test_run

    async def run_tests(
        self,
        db: AsyncSession,
        project_id: str,
        test_ids: list[str] | None = None,
        triggered_by: str = "user",
        run_type: str = "manual",
    ) -> TestRun:
        test_run, project, tests = await self.prepare_run(
            db, project_id, test_ids, triggered_by, run_type
        )
        if test_run.execution_mode == "farm":
            from app.tasks.test_tasks import dispatch_farm_run

            dispatch_farm_run(test_run, project, tests)
            return test_run
        return await self.run_tests_local(db, test_run, project, tests)

    async def finalize_farm_run(
        self,
        db: AsyncSession,
        run_id: str,
        raw_results: list[dict[str, Any]],
    ) -> TestRun:
        test_run = (await db.execute(select(TestRun).where(TestRun.id == run_id))).scalar_one()
        tests = (
            await db.execute(
                select(GeneratedTest).where(GeneratedTest.project_id == test_run.project_id)
            )
        ).scalars().all()
        tests_by_id = {t.id: t for t in tests}

        ordered_tests: list[GeneratedTest] = []
        ordered_results: list[dict[str, Any]] = []
        for item in raw_results:
            if not item:
                continue
            test_id = item.get("test_id")
            if test_id and test_id in tests_by_id:
                ordered_tests.append(tests_by_id[test_id])
                ordered_results.append(item)

        await self._persist_results(db, test_run, ordered_tests, ordered_results)
        return test_run

    async def _persist_results(
        self,
        db: AsyncSession,
        test_run: TestRun,
        tests: list[GeneratedTest],
        results: list[dict[str, Any]],
    ) -> None:
        pass_count = 0
        fail_count = 0
        for test, result in zip(tests, results, strict=False):
            rel_screenshot = (
                artifact_service.to_relative(result["screenshot_path"])
                if result.get("screenshot_path")
                else None
            )
            rel_trace = (
                artifact_service.to_relative(result["trace_path"]) if result.get("trace_path") else None
            )
            run_result = TestRunResult(
                test_run_id=test_run.id,
                generated_test_id=test.id,
                status=result["status"],
                duration_ms=result.get("duration_ms"),
                failure_category=result.get("failure_category"),
                error_message=result.get("error_message"),
                screenshot_path=rel_screenshot,
                trace_path=rel_trace,
                video_path=result.get("video_path"),
            )
            db.add(run_result)
            await db.flush()

            if result["status"] == "passed":
                pass_count += 1
            else:
                fail_count += 1
                ai_summary = await failure_analysis_service.analyze(db, run_result, test)
                run_result.ai_summary = ai_summary
                if result.get("failure_category") == "selector drift":
                    await selector_healing_service.suggest_healing(db, run_result, test)

        test_run.status = "completed"
        test_run.completed_at = datetime.now(timezone.utc)
        await db.commit()

        logger.log(
            "run_completed",
            f"Run completed: {pass_count} passed, {fail_count} failed",
            project_id=test_run.project_id,
            execution_mode=test_run.execution_mode,
            parallel_workers=test_run.parallel_workers,
        )


test_execution_service = TestExecutionService()
