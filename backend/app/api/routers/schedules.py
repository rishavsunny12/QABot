from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.access import authorize_project
from app.core.auth_deps import AuthenticatedUser, get_current_user
from app.core.database import get_db
from app.models import TeamRole
from app.schemas import ScheduleCreate, ScheduleResponse, ScheduleUpdate
from app.services.schedule_service import schedule_service

router = APIRouter(tags=["schedules"])


def _to_response(schedule) -> ScheduleResponse:
    return ScheduleResponse(
        id=schedule.id,
        project_id=schedule.project_id,
        name=schedule.name,
        interval_minutes=schedule.interval_minutes,
        test_ids=schedule.test_ids_json,
        enabled=schedule.enabled,
        last_run_at=schedule.last_run_at,
        next_run_at=schedule.next_run_at,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
    )


async def _get_schedule_or_404(db: AsyncSession, schedule_id: str):
    schedule = await schedule_service.get(db, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.get("/projects/{project_id}/schedules", response_model=list[ScheduleResponse])
async def list_schedules(
    project_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await authorize_project(db, auth, project_id, TeamRole.VIEWER)
    schedules = await schedule_service.list_for_project(db, project_id)
    return [_to_response(s) for s in schedules]


@router.post("/projects/{project_id}/schedules", response_model=ScheduleResponse)
async def create_schedule(
    project_id: str,
    payload: ScheduleCreate,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await authorize_project(db, auth, project_id, TeamRole.ADMIN)
    schedule = await schedule_service.create(
        db,
        project_id,
        name=payload.name,
        interval_minutes=payload.interval_minutes,
        test_ids=payload.test_ids,
        enabled=payload.enabled,
    )
    return _to_response(schedule)


@router.patch("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: str,
    payload: ScheduleUpdate,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    schedule = await _get_schedule_or_404(db, schedule_id)
    await authorize_project(db, auth, schedule.project_id, TeamRole.ADMIN)
    updated = await schedule_service.update(
        db,
        schedule,
        name=payload.name,
        interval_minutes=payload.interval_minutes,
        test_ids=payload.test_ids,
        enabled=payload.enabled,
    )
    return _to_response(updated)


@router.delete("/schedules/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    schedule = await _get_schedule_or_404(db, schedule_id)
    await authorize_project(db, auth, schedule.project_id, TeamRole.ADMIN)
    await schedule_service.delete(db, schedule)
    return None


@router.post("/schedules/{schedule_id}/toggle", response_model=ScheduleResponse)
async def toggle_schedule(
    schedule_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    schedule = await _get_schedule_or_404(db, schedule_id)
    await authorize_project(db, auth, schedule.project_id, TeamRole.ADMIN)
    updated = await schedule_service.update(db, schedule, enabled=not schedule.enabled)
    return _to_response(updated)
