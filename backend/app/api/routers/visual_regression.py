from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.access import authorize_project
from app.core.auth_deps import AuthenticatedUser, get_current_user
from app.core.database import get_db
from app.models import TeamRole, VisualComparisonResult
from app.schemas import (
    VisualBaselineResponse,
    VisualComparisonResultResponse,
    VisualComparisonRunResponse,
    VisualRunRequest,
)
from app.services.artifact_service import artifact_service
from app.services.visual_regression_service import visual_regression_service
from app.tasks.visual_tasks import run_visual_comparison_task

router = APIRouter(tags=["visual-regression"])


@router.post("/projects/{project_id}/visual-baselines/capture", response_model=list[VisualBaselineResponse])
async def capture_baselines(
    project_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await authorize_project(db, auth, project_id, TeamRole.MEMBER)
    try:
        baselines = await visual_regression_service.capture_baselines_from_crawl(db, project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [
        VisualBaselineResponse(
            id=b.id,
            project_id=b.project_id,
            page_id=b.page_id,
            url=b.url,
            label=b.label,
            screenshot_path=b.screenshot_path,
            captured_at=b.captured_at,
        )
        for b in baselines
    ]


@router.get("/projects/{project_id}/visual-baselines", response_model=list[VisualBaselineResponse])
async def list_baselines(
    project_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await authorize_project(db, auth, project_id, TeamRole.VIEWER)
    baselines = await visual_regression_service.list_baselines(db, project_id)
    return [
        VisualBaselineResponse(
            id=b.id,
            project_id=b.project_id,
            page_id=b.page_id,
            url=b.url,
            label=b.label,
            screenshot_path=b.screenshot_path,
            captured_at=b.captured_at,
        )
        for b in baselines
    ]


@router.post("/projects/{project_id}/visual-regression/run")
async def start_visual_run(
    project_id: str,
    payload: VisualRunRequest | None = None,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await authorize_project(db, auth, project_id, TeamRole.MEMBER)
    threshold = payload.threshold_percent if payload else 1.0
    baselines = await visual_regression_service.list_baselines(db, project_id)
    if not baselines:
        raise HTTPException(status_code=400, detail="No visual baselines. Capture baselines first.")
    task = run_visual_comparison_task.delay(project_id, threshold)
    return {"job_id": task.id, "status": "queued", "threshold_percent": threshold}


@router.get("/projects/{project_id}/visual-regression/runs", response_model=list[VisualComparisonRunResponse])
async def list_visual_runs(
    project_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await authorize_project(db, auth, project_id, TeamRole.VIEWER)
    runs = await visual_regression_service.list_runs(db, project_id)
    return [
        VisualComparisonRunResponse(
            id=r.id,
            project_id=r.project_id,
            status=r.status,
            threshold_percent=r.threshold_percent,
            pass_count=r.pass_count,
            fail_count=r.fail_count,
            started_at=r.started_at,
            completed_at=r.completed_at,
        )
        for r in runs
    ]


@router.get("/visual-regression/runs/{run_id}", response_model=VisualComparisonRunResponse)
async def get_visual_run(
    run_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    run = await visual_regression_service.get_run_with_results(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Visual run not found")
    await authorize_project(db, auth, run.project_id, TeamRole.VIEWER)
    return VisualComparisonRunResponse(
        id=run.id,
        project_id=run.project_id,
        status=run.status,
        threshold_percent=run.threshold_percent,
        pass_count=run.pass_count,
        fail_count=run.fail_count,
        started_at=run.started_at,
        completed_at=run.completed_at,
        results=[
            VisualComparisonResultResponse(
                id=r.id,
                run_id=r.run_id,
                baseline_id=r.baseline_id,
                page_url=r.page_url,
                baseline_path=r.baseline_path,
                current_path=r.current_path,
                diff_path=r.diff_path,
                diff_percent=r.diff_percent,
                status=r.status,
            )
            for r in run.results
        ],
    )


@router.get("/visual-regression/results/{result_id}/artifacts/{artifact_type}")
async def get_visual_artifact(
    result_id: str,
    artifact_type: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = (
        await db.execute(select(VisualComparisonResult).where(VisualComparisonResult.id == result_id))
    ).scalar_one_or_none()
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    run = await visual_regression_service.get_run_with_results(db, result.run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Visual run not found")
    await authorize_project(db, auth, run.project_id, TeamRole.VIEWER)

    path_map = {
        "baseline": result.baseline_path,
        "current": result.current_path,
        "diff": result.diff_path,
    }
    rel = path_map.get(artifact_type)
    if not rel:
        raise HTTPException(status_code=404, detail="Artifact not found")
    abs_path = artifact_service.resolve_path(rel)
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="Artifact file missing")
    return FileResponse(abs_path)
