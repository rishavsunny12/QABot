import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app


@pytest.mark.asyncio(loop_scope="session")
async def test_list_billing_plans():
    original_enabled = settings.billing_enabled
    settings.billing_enabled = True
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/billing/plans")
            assert response.status_code == 200
            plans = response.json()
            assert len(plans) >= 3
            slugs = {p["slug"] for p in plans}
            assert "free" in slugs
            assert "pro" in slugs
    finally:
        settings.billing_enabled = original_enabled


@pytest.mark.asyncio(loop_scope="session")
async def test_team_billing_usage_summary():
    original_mode = settings.auth_mode
    original_billing = settings.billing_enforcement
    original_enabled = settings.billing_enabled
    settings.auth_mode = "dev"
    settings.billing_enforcement = True
    settings.billing_enabled = True
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            login = await client.post(
                "/api/auth/dev-login",
                json={"email": "billing@example.com", "name": "Billing User"},
            )
            team_id = login.json()["teams"][0]["team_id"]
            cookies = login.cookies

            billing = await client.get(f"/api/billing/teams/{team_id}", cookies=cookies)
            assert billing.status_code == 200
            body = billing.json()
            assert body["plan"]["slug"] == "free"
            assert "test_runs" in body["usage"]
            assert body["usage"]["test_runs"]["used"] == 0
    finally:
        settings.auth_mode = original_mode
        settings.billing_enforcement = original_billing
        settings.billing_enabled = original_enabled


@pytest.mark.asyncio(loop_scope="session")
async def test_change_plan():
    original_mode = settings.auth_mode
    original_enabled = settings.billing_enabled
    settings.auth_mode = "dev"
    settings.billing_enabled = True
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            login = await client.post(
                "/api/auth/dev-login",
                json={"email": "upgrade@example.com", "name": "Upgrade User"},
            )
            team_id = login.json()["teams"][0]["team_id"]
            cookies = login.cookies

            change = await client.post(
                f"/api/billing/teams/{team_id}/change-plan",
                json={"plan_slug": "pro"},
                cookies=cookies,
            )
            assert change.status_code == 200
            assert change.json()["plan"]["slug"] == "pro"
    finally:
        settings.auth_mode = original_mode
        settings.billing_enabled = original_enabled


@pytest.mark.asyncio(loop_scope="session")
async def test_billing_disabled_by_default():
    assert settings.billing_enabled is False
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/billing/plans")
        assert response.status_code == 404
