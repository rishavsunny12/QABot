from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthenticatedUser, get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.services.auth_service import auth_service
from app.services.team_service import team_service

router = APIRouter(prefix="/auth", tags=["auth"])


class DevLoginRequest(BaseModel):
    email: EmailStr
    name: str | None = Field(default=None, max_length=255)


class TeamMembershipResponse(BaseModel):
    team_id: str
    team_name: str
    team_slug: str
    role: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    avatar_url: str | None
    teams: list[TeamMembershipResponse]


class AuthConfigResponse(BaseModel):
    mode: str
    oidc_configured: bool
    dev_login_enabled: bool


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(value=token, **auth_service.session_cookie_settings())


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(settings.session_cookie_name)


@router.get("/config", response_model=AuthConfigResponse)
async def auth_config():
    return AuthConfigResponse(
        mode=settings.auth_mode,
        oidc_configured=bool(settings.oidc_client_id and settings.oidc_discovery_url),
        dev_login_enabled=settings.auth_mode in {"dev", "disabled"},
    )


@router.post("/dev-login", response_model=UserResponse)
async def dev_login(payload: DevLoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    if settings.auth_mode not in {"dev", "disabled"}:
        raise HTTPException(status_code=403, detail="Dev login is disabled")
    try:
        user, token = await auth_service.dev_login(db, payload.email, payload.name)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    _set_session_cookie(response, token)
    teams = await team_service.get_user_teams(db, user.id)
    return _user_response(user, teams)


@router.get("/login")
async def login_redirect():
    if settings.auth_mode != "oidc":
        raise HTTPException(
            status_code=400,
            detail="OIDC login is not enabled. Use dev login or set AUTH_MODE=oidc.",
        )
    if not settings.oidc_client_id or not settings.oidc_discovery_url:
        raise HTTPException(status_code=503, detail="OIDC is not configured")

    import httpx
    from authlib.integrations.httpx_client import AsyncOAuth2Client

    async with httpx.AsyncClient() as client:
        metadata = (await client.get(settings.oidc_discovery_url)).json()

    oauth_client = AsyncOAuth2Client(
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret,
        scope="openid email profile",
        redirect_uri=settings.oidc_redirect_uri,
    )
    uri, _state = oauth_client.create_authorization_url(metadata["authorization_endpoint"])
    return RedirectResponse(uri)


@router.get("/callback")
async def oidc_callback(request: Request, db: AsyncSession = Depends(get_db)):
    if settings.auth_mode != "oidc":
        raise HTTPException(status_code=400, detail="OIDC is not enabled")

    import httpx
    from authlib.integrations.httpx_client import AsyncOAuth2Client

    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    async with httpx.AsyncClient() as client:
        metadata = (await client.get(settings.oidc_discovery_url)).json()

    oauth_client = AsyncOAuth2Client(
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret,
        redirect_uri=settings.oidc_redirect_uri,
    )
    token = await oauth_client.fetch_token(
        metadata["token_endpoint"],
        code=code,
        grant_type="authorization_code",
    )
    userinfo = await oauth_client.get(metadata["userinfo_endpoint"], token=token)
    claims = userinfo.json()

    try:
        _user, session_token = await auth_service.login_with_oidc_claims(db, claims)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    redirect = RedirectResponse(f"{settings.frontend_url}/")
    _set_session_cookie(redirect, session_token)
    return redirect


@router.get("/me", response_model=UserResponse)
async def get_me(
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    teams = await team_service.get_user_teams(db, auth.user.id)
    return _user_response(auth.user, teams)


@router.post("/logout")
async def logout(response: Response):
    _clear_session_cookie(response)
    return {"status": "logged_out"}


def _user_response(user, teams) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        teams=[
            TeamMembershipResponse(
                team_id=team.id,
                team_name=team.name,
                team_slug=team.slug,
                role=membership.role,
            )
            for team, membership in teams
        ],
    )
