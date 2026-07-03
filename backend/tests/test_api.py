import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio(loop_scope="session")
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio(loop_scope="session")
async def test_create_and_list_projects():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create = await client.post(
            "/api/projects",
            json={
                "name": "Test Project",
                "base_url": "https://example.com",
                "allowed_domains": ["example.com"],
                "seed_urls": ["https://example.com"],
            },
        )
        assert create.status_code == 200
        project = create.json()
        assert project["name"] == "Test Project"

        listing = await client.get("/api/projects")
        assert listing.status_code == 200
        assert len(listing.json()) >= 1


@pytest.mark.asyncio(loop_scope="session")
async def test_delete_project():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create = await client.post(
            "/api/projects",
            json={
                "name": "Delete Me",
                "base_url": "https://delete.example.com",
                "allowed_domains": ["delete.example.com"],
            },
        )
        project_id = create.json()["id"]
        delete = await client.delete(f"/api/projects/{project_id}")
        assert delete.status_code == 204

        get_resp = await client.get(f"/api/projects/{project_id}")
        assert get_resp.status_code == 404
