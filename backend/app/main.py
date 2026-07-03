import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import crawl, healing, projects, runs, schedules, tests, visual_regression
from app.core.config import settings
from app.core.database import Base, engine
from app.services.artifact_service import artifact_service

logging.basicConfig(level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    artifact_service.base_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="AutoQA Agent API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api")
app.include_router(crawl.router, prefix="/api")
app.include_router(tests.router, prefix="/api")
app.include_router(runs.router, prefix="/api")
app.include_router(healing.router, prefix="/api")
app.include_router(schedules.router, prefix="/api")
app.include_router(visual_regression.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "autoqa-backend"}


@app.get("/api/projects/{project_id}/screenshots/{page_id}")
async def get_page_screenshot(project_id: str, page_id: str):
    from fastapi import HTTPException
    from fastapi.responses import FileResponse
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models import Page

    async with AsyncSessionLocal() as db:
        page = (
            await db.execute(select(Page).where(Page.id == page_id, Page.project_id == project_id))
        ).scalar_one_or_none()
        if not page or not page.screenshot_path:
            raise HTTPException(status_code=404, detail="Screenshot not found")
        path = artifact_service.resolve_path(page.screenshot_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Screenshot file missing")
        return FileResponse(path)
