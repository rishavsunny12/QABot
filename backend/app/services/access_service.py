from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models import Project, ROLE_RANK, TeamMember, TeamRole, User
from app.services.team_service import team_service

logger = get_logger("AccessService")


class AccessService:
    """Authorize project access based on team membership and role."""

    async def get_accessible_team_ids(self, db: AsyncSession, user_id: str) -> list[str]:
        result = await db.execute(select(TeamMember.team_id).where(TeamMember.user_id == user_id))
        return list(result.scalars().all())

    async def list_accessible_projects(
        self, db: AsyncSession, user_id: str, team_id: str | None = None
    ) -> list[Project]:
        team_ids = await self.get_accessible_team_ids(db, user_id)
        if team_id:
            if team_id not in team_ids:
                return []
            team_ids = [team_id]

        if not team_ids:
            return []

        query = (
            select(Project)
            .where(Project.team_id.in_(team_ids))
            .order_by(Project.created_at.desc())
        )
        return list((await db.execute(query)).scalars().all())

    async def get_membership(
        self, db: AsyncSession, user_id: str, team_id: str
    ) -> TeamMember | None:
        return (
            await db.execute(
                select(TeamMember).where(
                    TeamMember.user_id == user_id,
                    TeamMember.team_id == team_id,
                )
            )
        ).scalar_one_or_none()

    async def ensure_project_access(
        self,
        db: AsyncSession,
        user: User,
        project_id: str,
        min_role: TeamRole = TeamRole.VIEWER,
    ) -> tuple[Project, TeamMember]:
        project = (
            await db.execute(select(Project).where(Project.id == project_id))
        ).scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")
        if not project.team_id:
            if settings.auth_mode == "disabled":
                system = await team_service.ensure_system_user(db)
                project.team_id = system.memberships[0].team_id
                await db.flush()
            else:
                raise PermissionError("Project is not assigned to a team")

        membership = await self.get_membership(db, user.id, project.team_id)
        if not membership:
            raise PermissionError("You do not have access to this project")
        if ROLE_RANK[membership.role] < ROLE_RANK[min_role.value]:
            raise PermissionError(f"Requires {min_role.value} role or higher")
        return project, membership

    async def ensure_run_access(
        self, db: AsyncSession, user: User, run_id: str, min_role: TeamRole = TeamRole.VIEWER
    ) -> tuple[Project, TeamMember]:
        from app.models import TestRun

        run = (await db.execute(select(TestRun).where(TestRun.id == run_id))).scalar_one_or_none()
        if not run:
            raise ValueError("Run not found")
        return await self.ensure_project_access(db, user, run.project_id, min_role)

    async def ensure_result_access(
        self, db: AsyncSession, user: User, result_id: str, min_role: TeamRole = TeamRole.VIEWER
    ) -> tuple[Project, TeamMember]:
        from app.models import TestRun, TestRunResult

        row = (
            await db.execute(
                select(TestRunResult, TestRun.project_id)
                .join(TestRun, TestRunResult.test_run_id == TestRun.id)
                .where(TestRunResult.id == result_id)
            )
        ).first()
        if not row:
            raise ValueError("Result not found")
        _, project_id = row
        return await self.ensure_project_access(db, user, project_id, min_role)


access_service = AccessService()
