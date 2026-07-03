import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio(loop_scope="session")
async def test_create_and_list_schedules():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project = await client.post(
            "/api/projects",
            json={
                "name": "Schedule Project",
                "base_url": "https://schedule.example.com",
                "allowed_domains": ["schedule.example.com"],
            },
        )
        project_id = project.json()["id"]

        create = await client.post(
            f"/api/projects/{project_id}/schedules",
            json={"name": "Hourly run", "interval_minutes": 60, "enabled": True},
        )
        assert create.status_code == 200
        body = create.json()
        assert body["name"] == "Hourly run"
        assert body["interval_minutes"] == 60
        assert body["enabled"] is True
        assert body["next_run_at"] is not None

        listing = await client.get(f"/api/projects/{project_id}/schedules")
        assert listing.status_code == 200
        assert len(listing.json()) == 1

        toggle = await client.post(f"/api/schedules/{body['id']}/toggle")
        assert toggle.status_code == 200
        assert toggle.json()["enabled"] is False

        delete = await client.delete(f"/api/schedules/{body['id']}")
        assert delete.status_code == 204
