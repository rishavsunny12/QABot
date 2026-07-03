from fastapi import APIRouter, Depends

from app.core.auth_deps import AuthenticatedUser, get_current_user
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas import ExecutionWorkersResponse
from app.tasks.celery_app import celery_app

router = APIRouter(prefix="/execution", tags=["execution"])
logger = get_logger("ExecutionRouter")


@router.get("/workers", response_model=ExecutionWorkersResponse)
async def get_worker_pool_status(auth: AuthenticatedUser = Depends(get_current_user)):
    active_workers = 0
    try:
        inspect = celery_app.control.inspect(timeout=1.0)
        active = inspect.active() if inspect else None
        active_workers = len(active) if active else 0
    except Exception as exc:
        logger.log("worker_inspect_failed", f"Could not inspect Celery workers: {exc}")

    return ExecutionWorkersResponse(
        mode="farm" if active_workers > 1 else "local",
        active_workers=active_workers,
        max_parallel_workers=settings.max_parallel_workers,
        default_parallel_workers=settings.default_parallel_workers,
    )
