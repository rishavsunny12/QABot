from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.access import authorize_project
from app.core.auth_deps import AuthenticatedUser, get_current_user
from app.core.database import get_db
from app.models import GeneratedTest, TeamRole, TestRun, TestRunResult
from app.schemas import RunTestsRequest, TestRunResponse, TestRunResultResponse
from app.services.access_service import access_service
from app.services.artifact_service import artifact_service
from app.tasks.test_tasks import run_tests_task

router = APIRouter(tags=["runs"])


def _run_response(run: TestRun, results: list[TestRunResult]) -> TestRunResponse:
    return TestRunResponse(
        id=run.id,
        project_id=run.project_id,
        run_type=run.run_type,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        triggered_by=run.triggered_by,
        parallel_workers=run.parallel_workers,
        execution_mode=run.execution_mode,
        pass_count=sum(1 for r in results if r.status == "passed"),
        fail_count=sum(1 for r in results if r.status == "failed"),
        total_count=len(results),
    )


@router.post("/projects/{project_id}/run-tests")
async def start_run(
    project_id: str,
    payload: RunTestsRequest | None = None,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await authorize_project(db, auth, project_id, TeamRole.MEMBER)
    test_ids = payload.test_ids if payload else None
    task = run_tests_task.delay(project_id, test_ids)
    return {"job_id": task.id, "status": "queued"}


@router.get("/runs/{run_id}", response_model=TestRunResponse)
async def get_run(
    run_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await access_service.ensure_run_access(db, auth.user, run_id, TeamRole.VIEWER)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    run = (await db.execute(select(TestRun).where(TestRun.id == run_id))).scalar_one()
    results = (
        await db.execute(select(TestRunResult).where(TestRunResult.test_run_id == run_id))
    ).scalars().all()
    return _run_response(run, results)


@router.get("/projects/{project_id}/runs", response_model=list[TestRunResponse])
async def list_runs(
    project_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await authorize_project(db, auth, project_id, TeamRole.VIEWER)
    runs = (
        await db.execute(
            select(TestRun)
            .where(TestRun.project_id == project_id)
            .order_by(TestRun.started_at.desc().nullslast())
        )
    ).scalars().all()
    responses = []
    for run in runs:
        results = (
            await db.execute(select(TestRunResult).where(TestRunResult.test_run_id == run.id))
        ).scalars().all()
        responses.append(_run_response(run, results))
    return responses


@router.get("/runs/{run_id}/results", response_model=list[TestRunResultResponse])
async def get_run_results(
    run_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await access_service.ensure_run_access(db, auth.user, run_id, TeamRole.VIEWER)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    result = await db.execute(
        select(TestRunResult, GeneratedTest.name)
        .join(GeneratedTest, TestRunResult.generated_test_id == GeneratedTest.id)
        .where(TestRunResult.test_run_id == run_id)
    )
    return [
        TestRunResultResponse(
            id=r.id,
            test_run_id=r.test_run_id,
            generated_test_id=r.generated_test_id,
            test_name=name,
            status=r.status,
            duration_ms=r.duration_ms,
            failure_category=r.failure_category,
            error_message=r.error_message,
            screenshot_path=r.screenshot_path,
            trace_path=r.trace_path,
            video_path=r.video_path,
            ai_summary=r.ai_summary,
        )
        for r, name in result.all()
    ]


@router.get("/results/{result_id}", response_model=TestRunResultResponse)
async def get_result(
    result_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await access_service.ensure_result_access(db, auth.user, result_id, TeamRole.VIEWER)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    result = await db.execute(
        select(TestRunResult, GeneratedTest.name)
        .join(GeneratedTest, TestRunResult.generated_test_id == GeneratedTest.id)
        .where(TestRunResult.id == result_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Result not found")
    r, name = row
    return TestRunResultResponse(
        id=r.id,
        test_run_id=r.test_run_id,
        generated_test_id=r.generated_test_id,
        test_name=name,
        status=r.status,
        duration_ms=r.duration_ms,
        failure_category=r.failure_category,
        error_message=r.error_message,
        screenshot_path=r.screenshot_path,
        trace_path=r.trace_path,
        video_path=r.video_path,
        ai_summary=r.ai_summary,
    )


@router.get("/results/{result_id}/artifacts/{artifact_type}")
async def get_artifact(
    result_id: str,
    artifact_type: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await access_service.ensure_result_access(db, auth.user, result_id, TeamRole.VIEWER)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    result = (
        await db.execute(select(TestRunResult).where(TestRunResult.id == result_id))
    ).scalar_one()
    path_map = {
        "screenshot": result.screenshot_path,
        "trace": result.trace_path,
        "video": result.video_path,
    }
    rel_path = path_map.get(artifact_type)
    if not rel_path:
        raise HTTPException(status_code=404, detail="Artifact not found")

    abs_path = artifact_service.resolve_path(rel_path)
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="Artifact file missing")
    return FileResponse(abs_path)
