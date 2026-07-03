from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import create_access_token, settings
from app.core.logging import get_logger
from app.models import User
from app.services.team_service import team_service

logger = get_logger("AuthService")


class AuthService:
    """User authentication via dev login or OIDC SSO."""

    async def upsert_user(
        self,
        db: AsyncSession,
        email: str,
        name: str,
        sso_subject: str | None = None,
        avatar_url: str | None = None,
    ) -> User:
        query = select(User).options(selectinload(User.memberships))
        if sso_subject:
            user = (
                await db.execute(query.where(User.sso_subject == sso_subject))
            ).scalar_one_or_none()
        else:
            user = (await db.execute(query.where(User.email == email))).scalar_one_or_none()

        if user:
            user.email = email
            user.name = name
            if sso_subject:
                user.sso_subject = sso_subject
            if avatar_url:
                user.avatar_url = avatar_url
        else:
            user = User(
                email=email,
                name=name,
                sso_subject=sso_subject,
                avatar_url=avatar_url,
            )
            db.add(user)
            await db.flush()
            await team_service.create_team(db, user, f"{name.split()[0]}'s Team")

        await db.commit()
        refreshed = (
            await db.execute(
                select(User).options(selectinload(User.memberships)).where(User.id == user.id)
            )
        ).scalar_one()
        return refreshed

    async def dev_login(self, db: AsyncSession, email: str, name: str | None = None) -> tuple[User, str]:
        if settings.auth_mode not in {"dev", "disabled"}:
            raise PermissionError("Dev login is disabled")
        user = await self.upsert_user(db, email=email, name=name or email.split("@")[0])
        token = create_access_token(user.id, user.email)
        logger.log("dev_login", f"User {email} signed in", user_id=user.id)
        return user, token

    async def login_with_oidc_claims(
        self, db: AsyncSession, claims: dict
    ) -> tuple[User, str]:
        email = claims.get("email")
        sub = claims.get("sub")
        name = claims.get("name") or claims.get("preferred_username") or email
        if not email or not sub:
            raise ValueError("OIDC claims missing email or sub")

        user = await self.upsert_user(
            db,
            email=email,
            name=name,
            sso_subject=sub,
            avatar_url=claims.get("picture"),
        )
        token = create_access_token(user.id, user.email)
        logger.log("oidc_login", f"User {email} signed in via SSO", user_id=user.id)
        return user, token

    def session_cookie_settings(self) -> dict:
        return {
            "key": settings.session_cookie_name,
            "httponly": True,
            "samesite": "lax",
            "secure": settings.frontend_url.startswith("https"),
            "max_age": settings.jwt_exp_hours * 3600,
        }


auth_service = AuthService()
