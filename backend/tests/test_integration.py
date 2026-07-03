"""Integration tests for AutoQA Agent API surface."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio(loop_scope="session")
async def test_full_project_lifecycle():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Health
        health = await client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        # Create project
        create = await client.post(
            "/api/projects",
            json={
                "name": "Integration App",
                "base_url": "https://demo.playwright.dev/todomvc",
                "allowed_domains": ["demo.playwright.dev"],
                "seed_urls": ["https://demo.playwright.dev/todomvc"],
            },
        )
        assert create.status_code == 200
        project = create.json()
        pid = project["id"]
        assert project["name"] == "Integration App"
        assert project["crawl_status"] == "idle"

        # Get project
        get_one = await client.get(f"/api/projects/{pid}")
        assert get_one.status_code == 200

        # Update project
        patch = await client.patch(
            f"/api/projects/{pid}",
            json={"name": "Integration App Updated"},
        )
        assert patch.status_code == 200
        assert patch.json()["name"] == "Integration App Updated"

        # List projects
        listing = await client.get("/api/projects")
        assert listing.status_code == 200
        assert any(p["id"] == pid for p in listing.json())

        # Crawl status (before crawl)
        status = await client.get(f"/api/projects/{pid}/crawl-status")
        assert status.status_code == 200
        assert status.json()["status"] == "idle"

        # Pages and flows (empty before crawl)
        pages = await client.get(f"/api/projects/{pid}/pages")
        assert pages.status_code == 200
        assert pages.json() == []

        flows = await client.get(f"/api/projects/{pid}/flows")
        assert flows.status_code == 200
        assert flows.json() == []

        graph = await client.get(f"/api/projects/{pid}/flow-graph")
        assert graph.status_code == 200
        assert graph.json()["nodes"] == []

        tests = await client.get(f"/api/projects/{pid}/tests")
        assert tests.status_code == 200
        assert tests.json() == []

        runs = await client.get(f"/api/projects/{pid}/runs")
        assert runs.status_code == 200
        assert runs.json() == []

        schedules = await client.get(f"/api/projects/{pid}/schedules")
        assert schedules.status_code == 200
        assert schedules.json() == []


@pytest.mark.asyncio(loop_scope="session")
async def test_schedule_lifecycle():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project = await client.post(
            "/api/projects",
            json={
                "name": "Schedule Lifecycle",
                "base_url": "https://example.com",
                "allowed_domains": ["example.com"],
            },
        )
        pid = project.json()["id"]

        create = await client.post(
            f"/api/projects/{pid}/schedules",
            json={"name": "Every hour", "interval_minutes": 60},
        )
        assert create.status_code == 200
        sid = create.json()["id"]

        toggle = await client.post(f"/api/schedules/{sid}/toggle")
        assert toggle.status_code == 200
        assert toggle.json()["enabled"] is False

        resume = await client.post(f"/api/schedules/{sid}/toggle")
        assert resume.status_code == 200
        assert resume.json()["enabled"] is True

        update = await client.patch(
            f"/api/schedules/{sid}",
            json={"name": "Updated schedule", "interval_minutes": 15},
        )
        assert update.status_code == 200
        assert update.json()["interval_minutes"] == 15

        delete = await client.delete(f"/api/schedules/{sid}")
        assert delete.status_code == 204


@pytest.mark.asyncio(loop_scope="session")
async def test_flow_inference_and_test_generation():
    """Verify flow inference and test generation services with synthetic crawl data."""
    from app.core.database import AsyncSessionLocal
    from app.models import Element, Page, Project
    from app.services.flow_inference_service import flow_inference_service
    from app.services.test_generation_service import test_generation_service

    async with AsyncSessionLocal() as db:
        project = Project(
            name="Flow Test",
            base_url="https://demo.playwright.dev/todomvc",
            allowed_domains_json=["demo.playwright.dev"],
            seed_urls_json=["https://demo.playwright.dev/todomvc"],
        )
        db.add(project)
        await db.flush()

        page = Page(
            project_id=project.id,
            url="https://demo.playwright.dev/todomvc",
            title="TodoMVC",
        )
        db.add(page)
        await db.flush()

        heading = Element(
            page_id=page.id,
            element_type="h1",
            text_content="todos",
            selector_primary="h1",
            selector_fallbacks_json=[],
            dom_signature_json={"tag": "h1"},
        )
        input_el = Element(
            page_id=page.id,
            element_type="input",
            aria_label="What needs to be done?",
            selector_primary='[aria-label="What needs to be done?"]',
            selector_fallbacks_json=[],
            dom_signature_json={"tag": "input"},
        )
        db.add_all([heading, input_el])
        await db.commit()

        flows = await flow_inference_service.infer_flows(db, project.id)
        assert len(flows) >= 1

        generated = await test_generation_service.generate_tests(db, project.id)
        assert len(generated) >= 1

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            export = await client.post(f"/api/tests/{generated[0].id}/export")
            assert export.status_code == 200
            assert "test(" in export.text
            assert "playwright" in export.text.lower()


@pytest.mark.asyncio(loop_scope="session")
async def test_healing_and_failure_endpoints_exist():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Non-existent resources return 404, not 500
        result = await client.get("/api/results/nonexistent-id")
        assert result.status_code == 404

        healing = await client.get("/api/results/nonexistent-id/healing-suggestions")
        assert healing.status_code == 200
        assert healing.json() == []

        run = await client.get("/api/runs/nonexistent-id")
        assert run.status_code == 404
