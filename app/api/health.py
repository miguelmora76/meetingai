"""Health check endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Check application health — database connectivity and LLM config."""
    settings = get_settings()

    # Test DB connection
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    # Check LLM config
    llm_status = "configured" if settings.anthropic_api_key else "not configured"

    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "db": db_status,
        "llm": llm_status,
        "whisper_mode": settings.whisper_mode,
        "slack_enabled": settings.slack_enabled,
    }
