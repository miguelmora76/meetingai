"""
Admin endpoints — destructive operations protected by bearer token.

POST /admin/reset  truncates all data tables and removes uploaded files.
Requires Authorization: Bearer <ADMIN_TOKEN> header.
"""

import logging
import secrets
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

_bearer = HTTPBearer()

# Leaf tables first, then parents (respects FK constraints).
_TABLES = [
    "doc_chunks",
    "incident_chunks",
    "incident_action_items",
    "incident_timeline_events",
    "incident_postmortems",
    "incidents",
    "embedding_chunks",
    "decisions",
    "action_items",
    "summaries",
    "transcript_segments",
    "transcripts",
    "meetings",
    "documents",
]


def _require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> None:
    """Verify the bearer token matches ADMIN_TOKEN using constant-time comparison."""
    if not secrets.compare_digest(credentials.credentials, settings.admin_token):
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/reset", dependencies=[Depends(_require_admin)])
async def reset_database(db: AsyncSession = Depends(get_db)):
    """
    Truncate all data tables and delete uploaded files.

    Requires Authorization: Bearer <ADMIN_TOKEN> header.
    Intended for POC / demo resets only. Irreversible.
    """
    # Truncate all tables in dependency order
    for table in _TABLES:
        await db.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
    await db.commit()
    logger.warning("admin/reset: all tables truncated")

    # Remove uploaded files
    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    deleted_files = 0
    if upload_dir.exists():
        for f in upload_dir.iterdir():
            if f.is_file():
                f.unlink()
                deleted_files += 1
            elif f.is_dir():
                shutil.rmtree(f)
                deleted_files += 1
    logger.warning(f"admin/reset: removed {deleted_files} items from {upload_dir}")

    return {"status": "ok", "tables_truncated": _TABLES, "files_deleted": deleted_files}
