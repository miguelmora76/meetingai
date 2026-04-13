"""
Meetings API — upload recordings, trigger processing, view results.
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.limiter import limiter
from app.db.repository import MeetingRepository
from app.db.session import get_db
from app.models.schemas import (
    ActionItemSchema,
    DecisionSchema,
    MeetingDetail,
    MeetingListItem,
    MeetingListResponse,
    MeetingProcessResponse,
    MeetingUploadResponse,
    TranscriptSchema,
    TranscriptSegmentSchema,
)
from app.workers.tasks import process_meeting_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/meetings", tags=["meetings"])

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".mp4", ".webm", ".m4a", ".ogg", ".flac"}


@router.post("/upload", response_model=MeetingUploadResponse, status_code=201)
@limiter.limit("10/minute")
async def upload_meeting(
    request: Request,
    file: UploadFile,
    title: str,
    date: datetime | None = None,
    participants: str | None = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Upload a meeting recording (audio or video)."""
    # Validate file extension
    suffix = Path(file.filename).suffix.lower() if file.filename else ""
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported file type '{suffix}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Read file and check size
    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            413,
            f"File too large. Maximum size: {settings.max_upload_size_mb} MB",
        )

    # Parse participants
    participant_list = []
    if participants:
        participant_list = [p.strip() for p in participants.split(",") if p.strip()]

    # Create DB record first — if this fails, no file is written
    repo = MeetingRepository(db)
    meeting = await repo.create_meeting(
        title=title,
        file_path=None,
        file_name=file.filename,
        file_size_bytes=len(content),
        date=date,
        participants=participant_list,
        status="uploading",
    )

    # Save to disk after DB record exists
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_name = f"{meeting.id}{suffix}"
    file_path = upload_dir / file_name

    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except OSError as e:
        # Clean up the orphaned DB record and re-raise
        await db.delete(meeting)
        await db.commit()
        raise HTTPException(500, f"Failed to save uploaded file: {e}") from e

    # Update the record with the file path and move to uploaded status
    await repo.update_meeting_file_path(meeting.id, str(file_path))
    await repo.update_meeting_status(meeting.id, "uploaded")

    logger.info(f"Meeting uploaded: {meeting.id} ({file.filename}, {len(content)} bytes)")

    return MeetingUploadResponse(
        id=meeting.id,
        title=meeting.title,
        status=meeting.status,
        file_name=meeting.file_name,
        file_size_mb=round(len(content) / (1024 * 1024), 2),
        created_at=meeting.created_at,
    )


@router.post("/{meeting_id}/process", response_model=MeetingProcessResponse, status_code=202)
async def process_meeting(
    meeting_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger async processing pipeline (transcribe → summarize → embed)."""
    repo = MeetingRepository(db)
    meeting = await repo.get_meeting(meeting_id)

    if not meeting:
        raise HTTPException(404, "Meeting not found")

    if meeting.status not in ("uploaded", "failed"):
        raise HTTPException(
            409,
            f"Meeting is currently '{meeting.status}'. Only 'uploaded' or 'failed' meetings can be processed.",
        )

    await repo.update_meeting_status(meeting_id, "processing")
    background_tasks.add_task(process_meeting_task, meeting_id)

    return MeetingProcessResponse(
        id=meeting_id,
        status="processing",
        message="Processing started. Poll GET /meetings/{id} for status updates.",
    )


@router.get("/{meeting_id}", response_model=MeetingDetail)
async def get_meeting(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get full meeting details including transcript, summary, action items, and decisions."""
    repo = MeetingRepository(db)
    meeting = await repo.get_meeting(meeting_id)

    if not meeting:
        raise HTTPException(404, "Meeting not found")

    # Build transcript schema
    transcript = None
    if meeting.transcript:
        segments = [
            TranscriptSegmentSchema(
                start_time=seg.start_time,
                end_time=seg.end_time,
                speaker=seg.speaker,
                text=seg.text,
            )
            for seg in (meeting.transcript.segments or [])
        ]
        transcript = TranscriptSchema(
            full_text=meeting.transcript.full_text,
            language=meeting.transcript.language,
            word_count=meeting.transcript.word_count,
            segments=segments,
        )

    return MeetingDetail(
        id=meeting.id,
        title=meeting.title,
        status=meeting.status,
        date=meeting.date,
        participants=meeting.participants or [],
        duration_seconds=meeting.duration_seconds,
        file_name=meeting.file_name,
        error_message=meeting.error_message,
        transcript=transcript,
        summary=meeting.summary.content if meeting.summary else None,
        action_items=[ActionItemSchema.model_validate(ai) for ai in (meeting.action_items or [])],
        decisions=[DecisionSchema.model_validate(d) for d in (meeting.decisions or [])],
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
    )


@router.get("", response_model=MeetingListResponse)
async def list_meetings(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all meetings with pagination."""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20

    repo = MeetingRepository(db)
    meetings, total = await repo.list_meetings(page=page, page_size=page_size, status=status)

    return MeetingListResponse(
        items=[MeetingListItem.model_validate(m) for m in meetings],
        total=total,
        page=page,
        page_size=page_size,
    )
