import asyncio

from app.core.database import AsyncSessionLocal
from app.services.crawler_service import crawler_service
from app.services.flow_inference_service import flow_inference_service
from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, name="crawl.run")
def run_crawl_task(self, project_id: str):
    async def _run():
        async with AsyncSessionLocal() as db:
            await crawler_service.run_crawl(db, project_id, self.request.id)
            await flow_inference_service.infer_flows(db, project_id)

    asyncio.run(_run())
    return {"status": "completed", "project_id": project_id}
