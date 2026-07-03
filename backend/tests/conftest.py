import os

import pytest_asyncio

# Set env before any app imports during test collection
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("CREDENTIALS_ENCRYPTION_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
os.environ.setdefault("ARTIFACTS_DIR", "/tmp/autoqa-artifacts")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("AUTH_MODE", "disabled")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-unit-tests-only")


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database():
    """Create schema once per session on the pytest asyncio event loop."""
    from app.core.database import Base, engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
