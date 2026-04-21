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

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.db.repository import IncidentRepository, MeetingRepository
from app.db.session import get_db
from app.models.schemas import (
    AirtableBasesListResponse,
    AirtableBaseSchema,
    AirtableFieldSchema,
    AirtableImportRequest,
    AirtableImportStatusResponse,
    AirtableTableSchema,
    AirtableTablesListResponse,
)
from app.services.airtable_connection import AirtableConnectionService
from app.services.airtable_import import AirtableImportService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/airtable", tags=["airtable"])

_AIRTABLE_META_BASES = "https://api.airtable.com/v0/meta/bases"


async def _get_user_token(db: AsyncSession) -> str:
    """Return the decrypted user PAT, or raise 400 if not connected."""
    service = AirtableConnectionService(db)
    token = await service.get_decrypted_token()
    if not token:
        raise HTTPException(400, "Airtable is not connected. POST /airtable/connect first.")
    return token


async def _airtable_get(path: str, token: str) -> dict:
    """Thin wrapper around Airtable meta GET calls. Translates status codes to HTTPException."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(path, headers={"Authorization": f"Bearer {token}"})
    if resp.status_code == 401:
        raise HTTPException(401, "Airtable rejected the stored token. Please reconnect.")
    if resp.status_code == 403:
        raise HTTPException(403, "Token is missing required scopes.")
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, f"Airtable error: {resp.text[:200]}")
    return resp.json()

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


# ── User-facing bases / tables listing ───────────────────────────────────


@router.get("/bases", response_model=AirtableBasesListResponse)
async def list_bases(db: AsyncSession = Depends(get_db)):
    """List all bases the connected user's PAT has access to."""
    token = await _get_user_token(db)
    data = await _airtable_get(_AIRTABLE_META_BASES, token)
    bases = [
        AirtableBaseSchema(
            id=b["id"],
            name=b.get("name", ""),
            permission_level=b.get("permissionLevel"),
        )
        for b in data.get("bases", [])
    ]
    return AirtableBasesListResponse(bases=bases)


@router.get("/bases/{base_id}/tables", response_model=AirtableTablesListResponse)
async def list_tables(base_id: str, db: AsyncSession = Depends(get_db)):
    """List tables and their fields for a given base."""
    token = await _get_user_token(db)
    data = await _airtable_get(f"{_AIRTABLE_META_BASES}/{base_id}/tables", token)
    tables = []
    for t in data.get("tables", []):
        fields = [
            AirtableFieldSchema(id=f["id"], name=f.get("name", ""), type=f.get("type", ""))
            for f in t.get("fields", [])
        ]
        tables.append(
            AirtableTableSchema(
                id=t["id"],
                name=t.get("name", ""),
                primary_field_id=t.get("primaryFieldId"),
                fields=fields,
            )
        )
    return AirtableTablesListResponse(base_id=base_id, tables=tables)


# ── Import: table → knowledge-base documents ─────────────────────────────


@router.post("/import", response_model=AirtableImportStatusResponse, status_code=202)
async def start_import(
    payload: AirtableImportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Kick off an import of an Airtable table into knowledge-base documents."""
    # Ensure the user has connected before accepting the job.
    await _get_user_token(db)

    service = AirtableImportService(db)
    row = await service.create_import(
        base_id=payload.base_id,
        base_name=payload.base_name,
        table_id=payload.table_id,
        table_name=payload.table_name,
        title_field=payload.title_field,
        content_fields=payload.content_fields,
    )

    # Import lazily to avoid circular references at module load.
    from app.workers.tasks import airtable_import_task

    background_tasks.add_task(airtable_import_task, row.id)
    return row


@router.get("/imports/{import_id}", response_model=AirtableImportStatusResponse)
async def get_import_status(import_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = AirtableImportService(db)
    row = await service.get_import(import_id)
    if not row:
        raise HTTPException(404, "Import not found")
    return row
