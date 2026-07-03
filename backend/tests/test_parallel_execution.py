import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio(loop_scope="session")
async def test_update_parallel_execution_settings():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project = await client.post(
            "/api/projects",
            json={
                "name": "Parallel Project",
                "base_url": "https://example.com",
                "allowed_domains": ["example.com"],
            },
        )
        pid = project.json()["id"]

        update = await client.patch(
            f"/api/projects/{pid}",
            json={"parallel_workers": 4, "execution_mode": "farm"},
        )
        assert update.status_code == 200
        body = update.json()
        assert body["parallel_workers"] == 4
        assert body["execution_mode"] == "farm"


@pytest.mark.asyncio(loop_scope="session")
async def test_execution_workers_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/execution/workers")
        assert response.status_code == 200
        body = response.json()
        assert "active_workers" in body
        assert body["max_parallel_workers"] >= 1
