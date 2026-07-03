import os

import pytest_asyncio

# Set env before any app imports during test collection
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("CREDENTIALS_ENCRYPTION_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
os.environ.setdefault("ARTIFACTS_DIR", "/tmp/autoqa-artifacts")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("AUTH_MODE", "disabled")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-unit-tests-only")
os.environ.setdefault("BILLING_ENFORCEMENT", "false")
os.environ.setdefault("BILLING_ENABLED", "false")


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database():
    """Create schema once per session on the pytest asyncio event loop."""
    from app.core.database import Base, AsyncSessionLocal, engine
    from app.services.billing_service import billing_service

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    if os.environ.get("BILLING_ENABLED", "false").lower() == "true":
        async with AsyncSessionLocal() as db:
            await billing_service.ensure_plans(db)
    yield
    await engine.dispose()
