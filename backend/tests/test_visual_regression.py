import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio(loop_scope="session")
async def test_visual_baseline_requires_crawl():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project = await client.post(
            "/api/projects",
            json={
                "name": "Visual Project",
                "base_url": "https://example.com",
                "allowed_domains": ["example.com"],
            },
        )
        pid = project.json()["id"]

        capture = await client.post(f"/api/projects/{pid}/visual-baselines/capture")
        assert capture.status_code == 400

        listing = await client.get(f"/api/projects/{pid}/visual-baselines")
        assert listing.status_code == 200
        assert listing.json() == []
