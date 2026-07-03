from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
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


@router.get("/projects/{project_id}/schedules", response_model=list[ScheduleResponse])
async def list_schedules(project_id: str, db: AsyncSession = Depends(get_db)):
    schedules = await schedule_service.list_for_project(db, project_id)
    return [_to_response(s) for s in schedules]


@router.post("/projects/{project_id}/schedules", response_model=ScheduleResponse)
async def create_schedule(
    project_id: str, payload: ScheduleCreate, db: AsyncSession = Depends(get_db)
):
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
    schedule_id: str, payload: ScheduleUpdate, db: AsyncSession = Depends(get_db)
):
    schedule = await schedule_service.get(db, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
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
async def delete_schedule(schedule_id: str, db: AsyncSession = Depends(get_db)):
    schedule = await schedule_service.get(db, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await schedule_service.delete(db, schedule)
    return None


@router.post("/schedules/{schedule_id}/toggle", response_model=ScheduleResponse)
async def toggle_schedule(schedule_id: str, db: AsyncSession = Depends(get_db)):
    schedule = await schedule_service.get(db, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    updated = await schedule_service.update(db, schedule, enabled=not schedule.enabled)
    return _to_response(updated)
