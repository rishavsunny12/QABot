"""Live verification of Playwright crawl and schedule processing."""

import asyncio

import pytest

from app.core.database import AsyncSessionLocal
from app.models import Project
from app.services.crawler_service import crawler_service
from app.services.flow_inference_service import flow_inference_service
from app.services.schedule_service import compute_next_run, schedule_service
from app.services.test_generation_service import test_generation_service
from app.services.test_execution_service import test_execution_service
from datetime import datetime, timezone, timedelta


@pytest.mark.asyncio(loop_scope="session")
async def test_live_crawl_todomvc():
    async with AsyncSessionLocal() as db:
        project = Project(
            name="Live Crawl",
            base_url="https://demo.playwright.dev/todomvc",
            allowed_domains_json=["demo.playwright.dev"],
            seed_urls_json=["https://demo.playwright.dev/todomvc"],
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)

        result = await crawler_service.run_crawl(db, project.id, job_id="live-test")
        assert result["pages_count"] >= 1
        assert result["elements_count"] >= 1

        flows = await flow_inference_service.infer_flows(db, project.id)
        assert len(flows) >= 3, f"Expected >=3 flows, got {len(flows)}"

        tests = await test_generation_service.generate_tests(db, project.id)
        assert len(tests) >= 1

        # Verify spec file exists on disk
        from app.services.artifact_service import artifact_service

        spec_path = artifact_service.resolve_path(tests[0].file_path)
        assert spec_path.exists()
        content = spec_path.read_text()
        assert "playwright" in content.lower()


@pytest.mark.asyncio(loop_scope="session")
async def test_schedule_triggers_due_run():
    async with AsyncSessionLocal() as db:
        project = Project(
            name="Schedule Due",
            base_url="https://demo.playwright.dev/todomvc",
            allowed_domains_json=["demo.playwright.dev"],
            seed_urls_json=["https://demo.playwright.dev/todomvc"],
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)

        await crawler_service.run_crawl(db, project.id, "sched-crawl")
        await flow_inference_service.infer_flows(db, project.id)
        await test_generation_service.generate_tests(db, project.id)

        schedule = await schedule_service.create(
            db, project.id, name="Due now", interval_minutes=60
        )
        schedule.next_run_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await db.commit()

        run_ids = await schedule_service.process_due_schedules(db)
        assert len(run_ids) >= 1

        from sqlalchemy import select
        from app.models import TestRun

        run = (
            await db.execute(select(TestRun).where(TestRun.id == run_ids[0]))
        ).scalar_one()
        assert run.run_type == "scheduled"
        assert run.status == "completed"
