from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthenticatedUser, get_current_user
from app.core.database import get_db
from app.models import TeamRole
from app.services.access_service import access_service
from app.services.team_service import team_service

router = APIRouter(prefix="/teams", tags=["teams"])


class TeamCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class TeamResponse(BaseModel):
    id: str
    name: str
    slug: str
    role: str


class TeamMemberResponse(BaseModel):
    id: str
    user_id: str
    email: str
    name: str
    role: str


class AddMemberRequest(BaseModel):
    email: EmailStr
    name: str | None = None
    role: TeamRole = TeamRole.MEMBER


class UpdateMemberRoleRequest(BaseModel):
    role: TeamRole


async def _require_team_admin(
    team_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    membership = await access_service.get_membership(db, auth.user.id, team_id)
    if not membership or membership.role not in {TeamRole.OWNER.value, TeamRole.ADMIN.value}:
        raise HTTPException(status_code=403, detail="Requires admin role")
    return membership


@router.get("", response_model=list[TeamResponse])
async def list_teams(
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    teams = await team_service.get_user_teams(db, auth.user.id)
    return [
        TeamResponse(id=team.id, name=team.name, slug=team.slug, role=membership.role)
        for team, membership in teams
    ]


@router.post("", response_model=TeamResponse)
async def create_team(
    payload: TeamCreateRequest,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    team, membership = await team_service.create_team(db, auth.user, payload.name)
    await db.commit()
    return TeamResponse(id=team.id, name=team.name, slug=team.slug, role=membership.role)


@router.get("/{team_id}/members", response_model=list[TeamMemberResponse])
async def list_team_members(
    team_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    membership = await access_service.get_membership(db, auth.user.id, team_id)
    if not membership:
        raise HTTPException(status_code=403, detail="You do not have access to this team")

    members = await team_service.list_members(db, team_id)
    return [
        TeamMemberResponse(
            id=member.id,
            user_id=user.id,
            email=user.email,
            name=user.name,
            role=member.role,
        )
        for member, user in members
    ]


@router.post("/{team_id}/members", response_model=TeamMemberResponse)
async def add_team_member(
    team_id: str,
    payload: AddMemberRequest,
    _: None = Depends(_require_team_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select

    from app.models import User

    try:
        member = await team_service.add_member_by_email(
            db, team_id, payload.email, payload.role, payload.name
        )
        await db.commit()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    user = (await db.execute(select(User).where(User.id == member.user_id))).scalar_one()
    return TeamMemberResponse(
        id=member.id,
        user_id=user.id,
        email=user.email,
        name=user.name,
        role=member.role,
    )


@router.patch("/{team_id}/members/{member_id}", response_model=TeamMemberResponse)
async def update_team_member_role(
    team_id: str,
    member_id: str,
    payload: UpdateMemberRoleRequest,
    _: None = Depends(_require_team_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        member = await team_service.update_member_role(db, team_id, member_id, payload.role)
        await db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    from sqlalchemy import select
    from app.models import User

    user = (await db.execute(select(User).where(User.id == member.user_id))).scalar_one()
    return TeamMemberResponse(
        id=member.id,
        user_id=user.id,
        email=user.email,
        name=user.name,
        role=member.role,
    )


@router.delete("/{team_id}/members/{member_id}", status_code=204)
async def remove_team_member(
    team_id: str,
    member_id: str,
    _: None = Depends(_require_team_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        await team_service.remove_member(db, team_id, member_id)
        await db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return None
