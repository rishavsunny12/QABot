import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth_deps import AuthenticatedUser
from app.core.logging import get_logger
from app.models import Team, TeamMember, TeamRole, User
from app.services.billing_service import billing_service

logger = get_logger("TeamService")

SYSTEM_USER_EMAIL = "system@autoqa.local"
SYSTEM_TEAM_SLUG = "default"


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "team"


class TeamService:
    """Team and membership management."""

    async def ensure_system_user(self, db: AsyncSession) -> AuthenticatedUser:
        user = (
            await db.execute(select(User).where(User.email == SYSTEM_USER_EMAIL))
        ).scalar_one_or_none()
        if not user:
            user = User(email=SYSTEM_USER_EMAIL, name="System User")
            db.add(user)
            await db.flush()

        team = (
            await db.execute(select(Team).where(Team.slug == SYSTEM_TEAM_SLUG))
        ).scalar_one_or_none()
        if not team:
            team = Team(name="Default Team", slug=SYSTEM_TEAM_SLUG)
            db.add(team)
            await db.flush()

        membership = (
            await db.execute(
                select(TeamMember).where(
                    TeamMember.team_id == team.id,
                    TeamMember.user_id == user.id,
                )
            )
        ).scalar_one_or_none()
        if not membership:
            membership = TeamMember(
                team_id=team.id,
                user_id=user.id,
                role=TeamRole.OWNER.value,
            )
            db.add(membership)
            await db.flush()

        await billing_service.ensure_team_subscription(db, team.id)
        await db.commit()
        refreshed = (
            await db.execute(
                select(User).options(selectinload(User.memberships)).where(User.id == user.id)
            )
        ).scalar_one()
        return AuthenticatedUser(user=refreshed, memberships=refreshed.memberships)

    async def get_user_teams(self, db: AsyncSession, user_id: str) -> list[tuple[Team, TeamMember]]:
        result = await db.execute(
            select(Team, TeamMember)
            .join(TeamMember, TeamMember.team_id == Team.id)
            .where(TeamMember.user_id == user_id)
            .order_by(Team.name)
        )
        return list(result.all())

    async def create_team(
        self, db: AsyncSession, user: User, name: str
    ) -> tuple[Team, TeamMember]:
        base_slug = slugify(name)
        slug = base_slug
        suffix = 1
        while (await db.execute(select(Team).where(Team.slug == slug))).scalar_one_or_none():
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        team = Team(name=name, slug=slug)
        db.add(team)
        await db.flush()
        membership = TeamMember(
            team_id=team.id,
            user_id=user.id,
            role=TeamRole.OWNER.value,
        )
        db.add(membership)
        await db.flush()
        await billing_service.ensure_team_subscription(db, team.id)
        logger.log("team_created", f"Team {name} created", team_id=team.id, user_id=user.id)
        return team, membership

    async def add_member_by_email(
        self,
        db: AsyncSession,
        team_id: str,
        email: str,
        role: TeamRole = TeamRole.MEMBER,
        name: str | None = None,
    ) -> TeamMember:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if not user:
            user = User(email=email, name=name or email.split("@")[0])
            db.add(user)
            await db.flush()

        existing = (
            await db.execute(
                select(TeamMember).where(
                    TeamMember.team_id == team_id,
                    TeamMember.user_id == user.id,
                )
            )
        ).scalar_one_or_none()
        if existing:
            existing.role = role.value
            await db.flush()
            return existing

        membership = TeamMember(team_id=team_id, user_id=user.id, role=role.value)
        db.add(membership)
        await db.flush()
        return membership

    async def list_members(self, db: AsyncSession, team_id: str) -> list[tuple[TeamMember, User]]:
        result = await db.execute(
            select(TeamMember, User)
            .join(User, TeamMember.user_id == User.id)
            .where(TeamMember.team_id == team_id)
            .order_by(TeamMember.created_at)
        )
        return list(result.all())

    async def update_member_role(
        self, db: AsyncSession, team_id: str, member_id: str, role: TeamRole
    ) -> TeamMember:
        membership = (
            await db.execute(
                select(TeamMember).where(
                    TeamMember.id == member_id,
                    TeamMember.team_id == team_id,
                )
            )
        ).scalar_one_or_none()
        if not membership:
            raise ValueError("Team member not found")
        membership.role = role.value
        await db.flush()
        return membership

    async def remove_member(self, db: AsyncSession, team_id: str, member_id: str) -> None:
        membership = (
            await db.execute(
                select(TeamMember).where(
                    TeamMember.id == member_id,
                    TeamMember.team_id == team_id,
                )
            )
        ).scalar_one_or_none()
        if not membership:
            raise ValueError("Team member not found")
        if membership.role == TeamRole.OWNER.value:
            owners = (
                await db.execute(
                    select(TeamMember).where(
                        TeamMember.team_id == team_id,
                        TeamMember.role == TeamRole.OWNER.value,
                    )
                )
            ).scalars().all()
            if len(owners) <= 1:
                raise ValueError("Cannot remove the last team owner")
        await db.delete(membership)
        await db.flush()


team_service = TeamService()
