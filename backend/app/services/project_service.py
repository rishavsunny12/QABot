from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import (
    Element,
    Flow,
    FlowStep,
    GeneratedTest,
    HealingSuggestion,
    Page,
    PageTransition,
    Project,
    ProjectCredential,
    TestRun,
    TestRunResult,
    TestSchedule,
    VisualBaseline,
    VisualComparisonResult,
    VisualComparisonRun,
)
from app.services.artifact_service import artifact_service

logger = get_logger("ProjectService")


class ProjectService:
    """Project lifecycle operations."""

    async def delete_project(self, db: AsyncSession, project_id: str) -> None:
        project = (
            await db.execute(select(Project).where(Project.id == project_id))
        ).scalar_one_or_none()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        page_ids = select(Page.id).where(Page.project_id == project_id)
        flow_ids = select(Flow.id).where(Flow.project_id == project_id)
        test_ids = select(GeneratedTest.id).where(GeneratedTest.project_id == project_id)
        run_ids = select(TestRun.id).where(TestRun.project_id == project_id)

        await db.execute(
            delete(HealingSuggestion).where(
                HealingSuggestion.generated_test_id.in_(test_ids)
            )
        )
        await db.execute(
            delete(TestRunResult).where(TestRunResult.test_run_id.in_(run_ids))
        )
        await db.execute(delete(TestRun).where(TestRun.project_id == project_id))
        await db.execute(delete(TestSchedule).where(TestSchedule.project_id == project_id))
        await db.execute(delete(VisualComparisonResult).where(
            VisualComparisonResult.run_id.in_(
                select(VisualComparisonRun.id).where(VisualComparisonRun.project_id == project_id)
            )
        ))
        await db.execute(delete(VisualComparisonRun).where(VisualComparisonRun.project_id == project_id))
        await db.execute(delete(VisualBaseline).where(VisualBaseline.project_id == project_id))
        await db.execute(delete(GeneratedTest).where(GeneratedTest.project_id == project_id))
        await db.execute(delete(FlowStep).where(FlowStep.flow_id.in_(flow_ids)))
        await db.execute(delete(Flow).where(Flow.project_id == project_id))
        await db.execute(delete(PageTransition).where(PageTransition.project_id == project_id))
        await db.execute(delete(Element).where(Element.page_id.in_(page_ids)))
        await db.execute(delete(Page).where(Page.project_id == project_id))
        await db.execute(delete(ProjectCredential).where(ProjectCredential.project_id == project_id))
        await db.execute(delete(Project).where(Project.id == project_id))

        project_dir = artifact_service.project_dir(project_id)
        if project_dir.exists():
            import shutil

            shutil.rmtree(project_dir, ignore_errors=True)

        logger.log("project_deleted", f"Deleted project {project_id}", project_id=project_id)


project_service = ProjectService()
