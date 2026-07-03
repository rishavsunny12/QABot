from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.access import authorize_project
from app.api.billing_helpers import enforce_team_quota
from app.core.auth_deps import AuthenticatedUser, get_current_user
from app.core.database import get_db
from app.core.encryption import credential_encryption
from app.models import Project, ProjectCredential, TeamRole
from app.schemas import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.access_service import access_service
from app.services.project_service import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


def _to_response(project: Project, user_role: str | None = None) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        name=project.name,
        base_url=project.base_url,
        login_url=project.login_url,
        allowed_domains=project.allowed_domains_json or [],
        seed_urls=project.seed_urls_json or [],
        crawl_status=project.crawl_status,
        crawl_pages_count=project.crawl_pages_count,
        crawl_elements_count=project.crawl_elements_count,
        has_credentials=project.credentials is not None,
        parallel_workers=project.parallel_workers,
        execution_mode=project.execution_mode,
        team_id=project.team_id,
        user_role=user_role,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.post("", response_model=ProjectResponse)
async def create_project(
    payload: ProjectCreate,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    team_id = payload.team_id
    if not team_id:
        if not auth.memberships:
            raise HTTPException(status_code=400, detail="User has no team membership")
        team_id = auth.memberships[0].team_id
    else:
        membership = await access_service.get_membership(db, auth.user.id, team_id)
        if not membership or membership.role not in {TeamRole.MEMBER.value, TeamRole.ADMIN.value, TeamRole.OWNER.value}:
            raise HTTPException(status_code=403, detail="Cannot create projects in this team")

    await enforce_team_quota(db, team_id, "projects", quantity=1)

    project = Project(
        name=payload.name,
        base_url=payload.base_url,
        login_url=payload.login_url,
        allowed_domains_json=payload.allowed_domains,
        seed_urls_json=payload.seed_urls or [payload.base_url],
        team_id=team_id,
        created_by_user_id=auth.user.id,
    )
    db.add(project)
    await db.flush()

    if payload.username and payload.password:
        cred = ProjectCredential(
            project_id=project.id,
            username=payload.username,
            encrypted_password=credential_encryption.encrypt(payload.password),
            auth_strategy=payload.auth_strategy,
        )
        db.add(cred)

    await db.commit()
    await db.refresh(project, attribute_names=["credentials"])
    membership = await access_service.get_membership(db, auth.user.id, team_id)
    return _to_response(project, membership.role if membership else None)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    team_id: str | None = Query(default=None),
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    projects = await access_service.list_accessible_projects(db, auth.user.id, team_id)
    role_by_team = {m.team_id: m.role for m in auth.memberships}
    responses = []
    for project in projects:
        result = await db.execute(
            select(Project)
            .options(selectinload(Project.credentials))
            .where(Project.id == project.id)
        )
        loaded = result.scalar_one()
        responses.append(_to_response(loaded, role_by_team.get(project.team_id or "")))
    return responses


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await authorize_project(db, auth, project_id, TeamRole.VIEWER)
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.credentials))
        .where(Project.id == project_id)
    )
    project = result.scalar_one()
    membership = await access_service.get_membership(db, auth.user.id, project.team_id or "")
    return _to_response(project, membership.role if membership else None)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await authorize_project(db, auth, project_id, TeamRole.ADMIN)
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.credentials))
        .where(Project.id == project.id)
    )
    project = result.scalar_one()

    if payload.name is not None:
        project.name = payload.name
    if payload.base_url is not None:
        project.base_url = payload.base_url
    if payload.login_url is not None:
        project.login_url = payload.login_url
    if payload.allowed_domains is not None:
        project.allowed_domains_json = payload.allowed_domains
    if payload.seed_urls is not None:
        project.seed_urls_json = payload.seed_urls
    if payload.parallel_workers is not None:
        project.parallel_workers = payload.parallel_workers
    if payload.execution_mode is not None:
        project.execution_mode = payload.execution_mode

    if payload.username is not None or payload.password is not None:
        if not project.credentials:
            project.credentials = ProjectCredential(
                project_id=project.id,
                username=payload.username or "",
                encrypted_password=credential_encryption.encrypt(payload.password or ""),
                auth_strategy=payload.auth_strategy or "form",
            )
            db.add(project.credentials)
        else:
            if payload.username is not None:
                project.credentials.username = payload.username
            if payload.password is not None:
                project.credentials.encrypted_password = credential_encryption.encrypt(payload.password)
            if payload.auth_strategy is not None:
                project.credentials.auth_strategy = payload.auth_strategy

    await db.commit()
    await db.refresh(project, attribute_names=["credentials"])
    membership = await access_service.get_membership(db, auth.user.id, project.team_id or "")
    return _to_response(project, membership.role if membership else None)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await authorize_project(db, auth, project_id, TeamRole.ADMIN)
    try:
        await project_service.delete_project(db, project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return None
