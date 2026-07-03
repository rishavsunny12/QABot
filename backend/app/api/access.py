from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthenticatedUser
from app.models import Project, TeamRole
from app.services.access_service import access_service


async def authorize_project(
    db: AsyncSession,
    auth: AuthenticatedUser,
    project_id: str,
    min_role: TeamRole = TeamRole.VIEWER,
) -> Project:
    try:
        project, _membership = await access_service.ensure_project_access(
            db, auth.user, project_id, min_role
        )
        return project
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
