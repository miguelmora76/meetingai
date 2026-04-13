"""
Shared test fixtures for EngineerAI test suite.

Usage
-----
Tests that need the FastAPI app use the `client` fixture (httpx AsyncClient).
Tests that need settings overrides use `override_settings`.
The `ADMIN_TOKEN` env var is set to "test-admin-token" for all tests.
"""

import asyncio
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Ensure required env vars are present before the app is imported
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")
os.environ.setdefault("ADMIN_TOKEN", "test-admin-token")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://meetingai:meetingai@localhost:5432/meetingai_test",
)


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop shared across the entire test session.

    Prevents 'Event loop is closed' errors caused by background tasks
    (e.g. process_meeting_task) that outlive a per-test event loop, and
    keeps the module-level SQLAlchemy engine on a stable loop.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def client():
    """Return an async HTTP client that speaks directly to the ASGI app."""
    # Import after env vars are set so Settings validation passes
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def admin_headers() -> dict:
    """Authorization headers for the /admin/reset endpoint."""
    return {"Authorization": f"Bearer {os.environ['ADMIN_TOKEN']}"}
