"""
Incidents API — create incidents (form or file upload), trigger analysis, view results.
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.limiter import limiter
from app.db.repository import IncidentRepository
from app.db.session import get_db
from app.models.schemas import (
    IncidentActionItemSchema,
    IncidentCreateRequest,
    IncidentDetail,
    IncidentListItem,
    IncidentListResponse,
    IncidentPostmortemSchema,
    IncidentTimelineEventSchema,
    IncidentUploadResponse,
)
from app.workers.tasks import process_incident_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/incidents", tags=["incidents"])

ALLOWED_TEXT_EXTENSIONS = {
    ".txt", ".md", ".log", ".yaml", ".yml", ".json", ".csv", ".rst", ".py",
}


@router.post("", response_model=IncidentUploadResponse, status_code=201)
@limiter.limit("10/minute")
async def create_incident(
    request: Request,
    body: IncidentCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Create an incident from structured form input and start analysis."""
    repo = IncidentRepository(db)
    incident = await repo.create_incident(
        title=body.title,
        severity=body.severity,
        status=body.status,
        services_affected=body.services_affected,
        description=body.description,
        raw_text=body.description,
        occurred_at=body.occurred_at,
    )

    background_tasks.add_task(process_incident_task, incident.id)

    return IncidentUploadResponse(
        id=incident.id,
        title=incident.title,
        processing_status=incident.processing_status,
        created_at=incident.created_at,
    )


@router.post("/upload", response_model=IncidentUploadResponse, status_code=201)
@limiter.limit("10/minute")
async def upload_incident(
    request: Request,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    title: str = "",
    severity: str = "sev3",
    status: str = "open",
    services_affected: str | None = None,
    occurred_at: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Upload a text file (logs, runbook, description) and start analysis."""
    suffix = Path(file.filename).suffix.lower() if file.filename else ""
    if suffix not in ALLOWED_TEXT_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported file type '{suffix}'. Allowed: {', '.join(sorted(ALLOWED_TEXT_EXTENSIONS))}",
        )

    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(413, f"File too large. Maximum: {settings.max_upload_size_mb} MB")

    upload_dir = Path(settings.upload_dir) / "incidents"
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = uuid.uuid4()
    file_path = upload_dir / f"{file_id}{suffix}"
    with open(file_path, "wb") as f:
        f.write(content)

    services_list = [s.strip() for s in services_affected.split(",") if s.strip()] if services_affected else []

    repo = IncidentRepository(db)
    incident = await repo.create_incident(
        title=title,
        severity=severity,
        status=status,
        services_affected=services_list,
        file_path=str(file_path),
        file_name=file.filename,
        occurred_at=occurred_at,
    )

    background_tasks.add_task(process_incident_task, incident.id)

    logger.info(f"Incident uploaded: {incident.id} ({file.filename})")

    return IncidentUploadResponse(
        id=incident.id,
        title=incident.title,
        processing_status=incident.processing_status,
        file_name=incident.file_name,
        created_at=incident.created_at,
    )


@router.get("/{incident_id}", response_model=IncidentDetail)
async def get_incident(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get full incident details including postmortem, timeline, and action items."""
    repo = IncidentRepository(db)
    incident = await repo.get_incident(incident_id)

    if not incident:
        raise HTTPException(404, "Incident not found")

    postmortem = None
    if incident.postmortem:
        postmortem = IncidentPostmortemSchema.model_validate(incident.postmortem)

    timeline = [
        IncidentTimelineEventSchema.model_validate(ev)
        for ev in (incident.timeline_events or [])
    ]

    action_items = [
        IncidentActionItemSchema.model_validate(ai)
        for ai in (incident.action_items or [])
    ]

    return IncidentDetail(
        id=incident.id,
        title=incident.title,
        severity=incident.severity,
        status=incident.status,
        processing_status=incident.processing_status,
        services_affected=incident.services_affected or [],
        description=incident.description,
        raw_text=incident.raw_text,
        file_name=incident.file_name,
        error_message=incident.error_message,
        occurred_at=incident.occurred_at,
        resolved_at=incident.resolved_at,
        postmortem=postmortem,
        timeline=timeline,
        action_items=action_items,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
    )


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """List all incidents with pagination."""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20

    repo = IncidentRepository(db)
    incidents, total = await repo.list_incidents(page=page, page_size=page_size)

    return IncidentListResponse(
        items=[IncidentListItem.model_validate(i) for i in incidents],
        total=total,
        page=page,
        page_size=page_size,
    )
