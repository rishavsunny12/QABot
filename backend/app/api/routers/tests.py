from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.access import authorize_project
from app.core.auth_deps import AuthenticatedUser, get_current_user
from app.core.database import get_db
from app.models import Flow, GeneratedTest, TeamRole
from app.schemas import GenerateTestsRequest, GeneratedTestResponse
from app.services.test_generation_service import test_generation_service
from app.tasks.test_tasks import run_generate_tests_task

router = APIRouter(tags=["tests"])


@router.post("/projects/{project_id}/generate-tests")
async def generate_tests(
    project_id: str,
    payload: GenerateTestsRequest | None = None,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await authorize_project(db, auth, project_id, TeamRole.MEMBER)
    flow_ids = payload.flow_ids if payload else None
    task = run_generate_tests_task.delay(project_id, flow_ids)
    return {"job_id": task.id, "status": "queued"}


@router.get("/projects/{project_id}/tests", response_model=list[GeneratedTestResponse])
async def list_tests(
    project_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await authorize_project(db, auth, project_id, TeamRole.VIEWER)
    result = await db.execute(
        select(GeneratedTest, Flow.name)
        .outerjoin(Flow, GeneratedTest.flow_id == Flow.id)
        .where(GeneratedTest.project_id == project_id)
        .order_by(GeneratedTest.created_at.desc())
    )
    tests = []
    for test, flow_name in result.all():
        tests.append(
            GeneratedTestResponse(
                id=test.id,
                project_id=test.project_id,
                flow_id=test.flow_id,
                name=test.name,
                file_path=test.file_path,
                version=test.version,
                status=test.status,
                created_at=test.created_at,
                flow_name=flow_name,
            )
        )
    return tests


@router.get("/tests/{test_id}", response_model=GeneratedTestResponse)
async def get_test(
    test_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GeneratedTest, Flow.name)
        .outerjoin(Flow, GeneratedTest.flow_id == Flow.id)
        .where(GeneratedTest.id == test_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Test not found")
    test, flow_name = row
    await authorize_project(db, auth, test.project_id, TeamRole.VIEWER)
    return GeneratedTestResponse(
        id=test.id,
        project_id=test.project_id,
        flow_id=test.flow_id,
        name=test.name,
        file_path=test.file_path,
        version=test.version,
        status=test.status,
        created_at=test.created_at,
        flow_name=flow_name,
    )


@router.post("/tests/{test_id}/export")
async def export_test(
    test_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    test = (
        await db.execute(select(GeneratedTest).where(GeneratedTest.id == test_id))
    ).scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    await authorize_project(db, auth, test.project_id, TeamRole.VIEWER)
    name, content = await test_generation_service.export_test(db, test_id)
    return PlainTextResponse(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{name}.spec.ts"'},
    )
