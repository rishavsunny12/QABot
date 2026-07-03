from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.encryption import credential_encryption
from app.models import Project, ProjectCredential
from app.schemas import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project_service import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


def _to_response(project: Project) -> ProjectResponse:
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
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.post("", response_model=ProjectResponse)
async def create_project(payload: ProjectCreate, db: AsyncSession = Depends(get_db)):
    project = Project(
        name=payload.name,
        base_url=payload.base_url,
        login_url=payload.login_url,
        allowed_domains_json=payload.allowed_domains,
        seed_urls_json=payload.seed_urls or [payload.base_url],
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

    await db.refresh(project, attribute_names=["credentials"])
    return _to_response(project)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project).options(selectinload(Project.credentials)).order_by(Project.created_at.desc())
    )
    return [_to_response(p) for p in result.scalars().all()]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.credentials))
        .where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _to_response(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str, payload: ProjectUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.credentials))
        .where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

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

    await db.refresh(project, attribute_names=["credentials"])
    return _to_response(project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    try:
        await project_service.delete_project(db, project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return None
