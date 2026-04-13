"""Tests for the meetings API — upload validation and listing."""

import io

import pytest
from httpx import AsyncClient


def _fake_audio_file(name: str = "test.mp3", size: int = 1024) -> dict:
    """Build a multipart file payload."""
    return {"file": (name, io.BytesIO(b"x" * size), "audio/mpeg")}


@pytest.mark.asyncio
async def test_upload_valid_mp3(client: AsyncClient):
    """POST /meetings/upload with a valid .mp3 file must return 201."""
    response = await client.post(
        "/meetings/upload",
        files=_fake_audio_file("meeting.mp3"),
        params={"title": "Test Meeting"},
    )
    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert body["status"] in ("uploaded", "uploading")


@pytest.mark.asyncio
async def test_upload_disallowed_extension_returns_400(client: AsyncClient):
    """POST /meetings/upload with an unsupported extension must return 400."""
    response = await client.post(
        "/meetings/upload",
        files={"file": ("malware.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
        params={"title": "Bad File"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_file_too_large_returns_413(client: AsyncClient, monkeypatch):
    """POST /meetings/upload with a file exceeding the configured limit must return 413."""
    from app.config import settings as settings_module

    # Patch max size to 1 byte so any file is "too large"
    original = settings_module.get_settings()
    monkeypatch.setattr(original, "max_upload_size_mb", 0)

    response = await client.post(
        "/meetings/upload",
        files=_fake_audio_file("big.mp3", size=1024),
        params={"title": "Too Big"},
    )
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_list_meetings_returns_200(client: AsyncClient):
    """GET /meetings must return 200 with pagination fields."""
    response = await client.get("/meetings")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "total" in body
    assert "page" in body
    assert "page_size" in body


@pytest.mark.asyncio
async def test_get_nonexistent_meeting_returns_404(client: AsyncClient):
    """GET /meetings/{id} with an unknown UUID must return 404."""
    response = await client.get("/meetings/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
