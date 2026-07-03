import shutil
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models import Page, VisualBaseline, VisualComparisonResult, VisualComparisonRun
from app.services.artifact_service import artifact_service
from playwright_utils.visual_capture import capture_page_screenshot
from playwright_utils.visual_diff import compare_images

logger = get_logger("VisualRegressionService")


class VisualRegressionService:
    """Capture visual baselines and compare screenshots for regressions."""

    async def capture_baselines_from_crawl(
        self, db: AsyncSession, project_id: str, replace: bool = True
    ) -> list[VisualBaseline]:
        if replace:
            await db.execute(delete(VisualBaseline).where(VisualBaseline.project_id == project_id))

        pages = (
            await db.execute(select(Page).where(Page.project_id == project_id))
        ).scalars().all()
        if not pages:
            raise ValueError("No crawled pages found. Run discovery crawl first.")

        baselines: list[VisualBaseline] = []
        baseline_dir = artifact_service.project_dir(project_id) / "visual-baselines"
        baseline_dir.mkdir(parents=True, exist_ok=True)

        for page in pages:
            if not page.screenshot_path:
                continue
            src = artifact_service.resolve_path(page.screenshot_path)
            if not src.exists():
                continue
            dest = baseline_dir / f"{page.id}_baseline.png"
            shutil.copy2(src, dest)
            rel = artifact_service.to_relative(dest)
            baseline = VisualBaseline(
                project_id=project_id,
                page_id=page.id,
                url=page.url,
                label=page.title or page.url,
                screenshot_path=rel,
            )
            db.add(baseline)
            baselines.append(baseline)

        await db.flush()
        logger.log(
            "baselines_captured",
            f"Captured {len(baselines)} visual baselines",
            project_id=project_id,
        )
        return baselines

    async def list_baselines(self, db: AsyncSession, project_id: str) -> list[VisualBaseline]:
        result = await db.execute(
            select(VisualBaseline)
            .where(VisualBaseline.project_id == project_id)
            .order_by(VisualBaseline.captured_at.desc())
        )
        return list(result.scalars().all())

    async def list_runs(self, db: AsyncSession, project_id: str) -> list[VisualComparisonRun]:
        result = await db.execute(
            select(VisualComparisonRun)
            .where(VisualComparisonRun.project_id == project_id)
            .order_by(VisualComparisonRun.started_at.desc())
        )
        return list(result.scalars().all())

    async def get_run_with_results(
        self, db: AsyncSession, run_id: str
    ) -> VisualComparisonRun | None:
        result = await db.execute(
            select(VisualComparisonRun)
            .options(selectinload(VisualComparisonRun.results))
            .where(VisualComparisonRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def run_comparison(
        self,
        db: AsyncSession,
        project_id: str,
        threshold_percent: float = 1.0,
    ) -> VisualComparisonRun:
        baselines = await self.list_baselines(db, project_id)
        if not baselines:
            raise ValueError("No visual baselines. Capture baselines from crawl first.")

        run = VisualComparisonRun(
            project_id=project_id,
            status="running",
            threshold_percent=threshold_percent,
        )
        db.add(run)
        await db.flush()

        run_dir = artifact_service.project_dir(project_id) / "visual-runs" / run.id
        run_dir.mkdir(parents=True, exist_ok=True)

        pass_count = 0
        fail_count = 0

        for baseline in baselines:
            current_path = run_dir / f"{baseline.id}_current.png"
            diff_path = run_dir / f"{baseline.id}_diff.png"

            try:
                await capture_page_screenshot(baseline.url, current_path)
                baseline_abs = artifact_service.resolve_path(baseline.screenshot_path)
                diff_result = compare_images(
                    baseline_abs,
                    current_path,
                    diff_path,
                    threshold_percent=threshold_percent,
                )
                status = "passed" if diff_result.passed else "failed"
                if diff_result.passed:
                    pass_count += 1
                else:
                    fail_count += 1

                result = VisualComparisonResult(
                    run_id=run.id,
                    baseline_id=baseline.id,
                    page_url=baseline.url,
                    baseline_path=baseline.screenshot_path,
                    current_path=artifact_service.to_relative(current_path),
                    diff_path=artifact_service.to_relative(diff_path)
                    if diff_result.diff_path
                    else None,
                    diff_percent=diff_result.diff_percent,
                    status=status,
                )
                db.add(result)
            except Exception as exc:
                fail_count += 1
                db.add(
                    VisualComparisonResult(
                        run_id=run.id,
                        baseline_id=baseline.id,
                        page_url=baseline.url,
                        baseline_path=baseline.screenshot_path,
                        current_path="",
                        diff_path=None,
                        diff_percent=100.0,
                        status="failed",
                    )
                )
                logger.log(
                    "visual_compare_error",
                    f"Failed comparing {baseline.url}: {exc}",
                    project_id=project_id,
                )

        run.pass_count = pass_count
        run.fail_count = fail_count
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        await db.commit()

        logger.log(
            "visual_run_completed",
            f"Visual run: {pass_count} passed, {fail_count} failed",
            project_id=project_id,
        )
        return run


visual_regression_service = VisualRegressionService()
