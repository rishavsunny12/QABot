from dataclasses import dataclass

from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import decode_access_token, settings
from app.core.database import get_db
from app.models import Project, ROLE_RANK, TeamMember, TeamRole, User


@dataclass
class AuthenticatedUser:
    user: User
    memberships: list[TeamMember]


def _extract_token(request: Request, session_cookie: str | None) -> str | None:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.removeprefix("Bearer ").strip()
    return session_cookie


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_cookie: str | None = Cookie(default=None, alias=settings.session_cookie_name),
) -> AuthenticatedUser:
    if settings.auth_mode == "disabled":
        return await _get_or_create_system_user(db)

    token = _extract_token(request, session_cookie)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        payload = decode_access_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired session") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session payload")

    result = await db.execute(
        select(User)
        .options(selectinload(User.memberships))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return AuthenticatedUser(user=user, memberships=user.memberships)


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_cookie: str | None = Cookie(default=None, alias=settings.session_cookie_name),
) -> AuthenticatedUser | None:
    if settings.auth_mode == "disabled":
        return await _get_or_create_system_user(db)
    token = _extract_token(request, session_cookie)
    if not token:
        return None
    try:
        return await get_current_user(request, db, session_cookie)
    except HTTPException:
        return None


async def _get_or_create_system_user(db: AsyncSession) -> AuthenticatedUser:
    from app.services.team_service import team_service

    return await team_service.ensure_system_user(db)


def require_role(min_role: TeamRole):
    async def _dependency(
        project_id: str,
        auth: AuthenticatedUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> tuple[Project, TeamMember]:
        project = (
            await db.execute(select(Project).where(Project.id == project_id))
        ).scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if not project.team_id:
            if settings.auth_mode == "disabled":
                return project, auth.memberships[0]
            raise HTTPException(status_code=403, detail="Project is not assigned to a team")

        membership = next(
            (m for m in auth.memberships if m.team_id == project.team_id),
            None,
        )
        if not membership:
            raise HTTPException(status_code=403, detail="You do not have access to this project")
        if ROLE_RANK[membership.role] < ROLE_RANK[min_role.value]:
            raise HTTPException(status_code=403, detail=f"Requires {min_role.value} role or higher")
        return project, membership

    return _dependency
