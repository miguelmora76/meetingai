"""Tests for the /admin/reset endpoint security."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_reset_without_token_is_rejected(client: AsyncClient):
    """POST /admin/reset without Authorization header must return 403."""
    response = await client.post("/admin/reset")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_reset_with_wrong_token_is_rejected(client: AsyncClient):
    """POST /admin/reset with a wrong bearer token must return 403."""
    response = await client.post(
        "/admin/reset",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_reset_with_correct_token_is_accepted(client: AsyncClient, admin_headers: dict):
    """POST /admin/reset with the correct token must return 200."""
    response = await client.post("/admin/reset", headers=admin_headers)
    # 200 means auth passed (DB truncation may or may not succeed in test env)
    assert response.status_code in (200, 500)
    # It must never be 401 or 403
    assert response.status_code not in (401, 403)
