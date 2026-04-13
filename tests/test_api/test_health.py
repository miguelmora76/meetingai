"""Tests for the health check endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient):
    """GET /health must return 200."""
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_shape(client: AsyncClient):
    """GET /health must include expected fields."""
    response = await client.get("/health")
    body = response.json()
    assert "status" in body
    assert "db" in body
    assert "llm" in body


@pytest.mark.asyncio
async def test_health_llm_reports_configured_when_key_set(client: AsyncClient):
    """GET /health must report llm=configured when ANTHROPIC_API_KEY is set."""
    response = await client.get("/health")
    body = response.json()
    # ANTHROPIC_API_KEY is set to "test-key-not-real" in conftest
    assert body["llm"] == "configured"
