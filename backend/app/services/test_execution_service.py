from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import GeneratedTest, Project, TestRun, TestRunResult
from app.services.artifact_service import artifact_service
from app.services.failure_analysis_service import failure_analysis_service
from app.services.selector_healing_service import selector_healing_service
from playwright_utils.executor import execute_specs

logger = get_logger("TestExecutionService")


class TestExecutionService:
    """Queue and execute Playwright tests."""

    async def run_tests(
        self,
        db: AsyncSession,
        project_id: str,
        test_ids: list[str] | None = None,
        triggered_by: str = "user",
        run_type: str = "manual",
    ) -> TestRun:
        query = select(GeneratedTest).where(GeneratedTest.project_id == project_id)
        if test_ids:
            query = query.where(GeneratedTest.id.in_(test_ids))
        tests = (await db.execute(query)).scalars().all()
        if not tests:
            raise ValueError("No tests found to run")

        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one()
        test_run = TestRun(
            project_id=project_id,
            run_type=run_type,
            status="running",
            started_at=datetime.now(timezone.utc),
            triggered_by=triggered_by,
        )
        db.add(test_run)
        await db.flush()

        run_dir = artifact_service.run_dir(test_run.id)
        spec_paths = [str(artifact_service.resolve_path(t.file_path)) for t in tests]
        results = execute_specs(spec_paths, run_dir, base_url=project.base_url)

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
            project_id=project_id,
        )
        return test_run


test_execution_service = TestExecutionService()
