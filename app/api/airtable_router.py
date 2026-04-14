"""
Airtable webhook router — receives status-change notifications from Airtable
automations and updates the local DB accordingly (bidirectional sync).

Setup in Airtable:
  1. Create an automation: "When a field changes → Send HTTP POST"
  2. URL: {APP_BASE_URL}/airtable/webhook
  3. Header: Authorization: Bearer {AIRTABLE_WEBHOOK_SECRET}
  4. Body (JSON):
       {
         "resource_type": "incident",
         "engineerai_id": "{EngineerAI ID}",
         "status": "{Status}"
       }
     For meetings substitute "resource_type": "meeting".

Security: The shared secret in the Authorization header is validated against
AIRTABLE_WEBHOOK_SECRET in settings. Requests with a missing or wrong secret
are rejected with 401. If AIRTABLE_WEBHOOK_SECRET is empty the endpoint is
disabled (returns 403) to prevent accidental open access.
"""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.db.repository import IncidentRepository, MeetingRepository
from app.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/airtable", tags=["airtable"])

VALID_RESOURCE_TYPES = {"incident", "meeting"}
VALID_INCIDENT_STATUSES = {"open", "mitigated", "resolved", "closed"}
VALID_MEETING_STATUSES = {"uploaded", "processing", "completed", "failed"}


class AirtableWebhookPayload(BaseModel):
    resource_type: str
    engineerai_id: uuid.UUID
    status: str
    resolved_at: datetime | None = None


def _verify_secret(request: Request, settings: Settings) -> None:
    """Raise 401/403 if the Authorization header does not match the configured secret."""
    if not settings.airtable_webhook_secret:
        raise HTTPException(403, "Airtable webhook is not configured (AIRTABLE_WEBHOOK_SECRET not set)")

    auth = request.headers.get("Authorization", "")
    expected = f"Bearer {settings.airtable_webhook_secret}"
    if auth != expected:
        raise HTTPException(401, "Invalid or missing webhook secret")


@router.post("/webhook")
async def airtable_webhook(
    request: Request,
    payload: AirtableWebhookPayload,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Receive a status update from an Airtable automation and apply it to the DB.
    Returns {"ok": true} on success.
    """
    _verify_secret(request, settings)

    if payload.resource_type not in VALID_RESOURCE_TYPES:
        raise HTTPException(
            400,
            f"Unknown resource_type '{payload.resource_type}'. Must be one of: {sorted(VALID_RESOURCE_TYPES)}",
        )

    resource_id = payload.engineerai_id

    if payload.resource_type == "incident":
        if payload.status not in VALID_INCIDENT_STATUSES:
            raise HTTPException(
                400,
                f"Invalid incident status '{payload.status}'. Must be one of: {sorted(VALID_INCIDENT_STATUSES)}",
            )
        repo = IncidentRepository(db)
        incident = await repo.get_incident(resource_id)
        if not incident:
            raise HTTPException(404, f"Incident {resource_id} not found")

        await repo.update_incident_status(
            resource_id,
            status=payload.status,
            resolved_at=payload.resolved_at,
        )
        logger.info(f"[airtable-webhook] Incident {resource_id} status → {payload.status}")

    elif payload.resource_type == "meeting":
        if payload.status not in VALID_MEETING_STATUSES:
            raise HTTPException(
                400,
                f"Invalid meeting status '{payload.status}'. Must be one of: {sorted(VALID_MEETING_STATUSES)}",
            )
        repo = MeetingRepository(db)
        meeting = await repo.get_meeting(resource_id)
        if not meeting:
            raise HTTPException(404, f"Meeting {resource_id} not found")

        await repo.update_meeting_status(resource_id, status=payload.status)
        logger.info(f"[airtable-webhook] Meeting {resource_id} status → {payload.status}")

    return {"ok": True}
