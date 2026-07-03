import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app


@pytest.mark.asyncio(loop_scope="session")
async def test_auth_config():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/auth/config")
        assert response.status_code == 200
        assert "mode" in response.json()


@pytest.mark.asyncio(loop_scope="session")
async def test_dev_login_and_me():
    original_mode = settings.auth_mode
    settings.auth_mode = "dev"
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            login = await client.post(
                "/api/auth/dev-login",
                json={"email": "alice@example.com", "name": "Alice"},
            )
            assert login.status_code == 200
            body = login.json()
            assert body["email"] == "alice@example.com"
            assert len(body["teams"]) >= 1

            me = await client.get("/api/auth/me", cookies=login.cookies)
            assert me.status_code == 200
            assert me.json()["email"] == "alice@example.com"
    finally:
        settings.auth_mode = original_mode


@pytest.mark.asyncio(loop_scope="session")
async def test_team_member_management():
    original_mode = settings.auth_mode
    settings.auth_mode = "dev"
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            owner_login = await client.post(
                "/api/auth/dev-login",
                json={"email": "owner@example.com", "name": "Owner"},
            )
            team_id = owner_login.json()["teams"][0]["team_id"]
            cookies = owner_login.cookies

            add_member = await client.post(
                f"/api/teams/{team_id}/members",
                json={"email": "viewer@example.com", "role": "viewer"},
                cookies=cookies,
            )
            assert add_member.status_code == 200
            assert add_member.json()["role"] == "viewer"

            members = await client.get(f"/api/teams/{team_id}/members", cookies=cookies)
            assert members.status_code == 200
            assert len(members.json()) >= 2
    finally:
        settings.auth_mode = original_mode


@pytest.mark.asyncio(loop_scope="session")
async def test_project_scoped_to_team():
    original_mode = settings.auth_mode
    settings.auth_mode = "dev"
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            login = await client.post(
                "/api/auth/dev-login",
                json={"email": "builder@example.com", "name": "Builder"},
            )
            cookies = login.cookies
            team_id = login.json()["teams"][0]["team_id"]

            create = await client.post(
                "/api/projects",
                json={
                    "name": "Team Project",
                    "base_url": "https://example.com",
                    "allowed_domains": ["example.com"],
                    "team_id": team_id,
                },
                cookies=cookies,
            )
            assert create.status_code == 200
            assert create.json()["team_id"] == team_id
            assert create.json()["user_role"] == "owner"
    finally:
        settings.auth_mode = original_mode
