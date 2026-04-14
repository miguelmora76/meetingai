"""
Pydantic schemas for API request/response serialization.

These are decoupled from the SQLAlchemy ORM models to keep the API contract
independent of the database layer.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# ── Meeting Schemas ───────────────────────────────────────────────────────


class MeetingUploadResponse(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    file_name: str | None = None
    file_size_mb: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MeetingProcessResponse(BaseModel):
    id: uuid.UUID
    status: str
    message: str


class MeetingListItem(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    date: datetime | None = None
    duration_seconds: int | None = None
    participants: list[str] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class MeetingListResponse(BaseModel):
    items: list[MeetingListItem]
    total: int
    page: int
    page_size: int


# ── Transcript Schemas ────────────────────────────────────────────────────


class TranscriptSegmentSchema(BaseModel):
    start_time: float
    end_time: float
    speaker: str | None = None
    text: str

    model_config = {"from_attributes": True}


class TranscriptSchema(BaseModel):
    full_text: str
    language: str = "en"
    word_count: int | None = None
    segments: list[TranscriptSegmentSchema] = []

    model_config = {"from_attributes": True}


# ── Summary / Extraction Schemas ──────────────────────────────────────────


class ActionItemSchema(BaseModel):
    id: uuid.UUID | None = None
    description: str
    assignee: str | None = None
    due_date: datetime | None = None
    priority: str = "medium"
    status: str = "open"
    source_quote: str | None = None

    model_config = {"from_attributes": True}


class DecisionSchema(BaseModel):
    id: uuid.UUID | None = None
    description: str
    participants: list[str] = []
    rationale: str | None = None
    source_quote: str | None = None

    model_config = {"from_attributes": True}


# ── Full Meeting Detail ──────────────────────────────────────────────────


class MeetingDetail(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    date: datetime | None = None
    participants: list[str] = []
    duration_seconds: int | None = None
    file_name: str | None = None
    error_message: str | None = None
    transcript: TranscriptSchema | None = None
    summary: str | None = None
    action_items: list[ActionItemSchema] = []
    decisions: list[DecisionSchema] = []
    airtable_record_id: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Search & RAG Schemas ─────────────────────────────────────────────────


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    # Polymorphic scope: source_type=meeting|incident|doc; source_id scopes to a single item
    source_type: str | None = None
    source_id: uuid.UUID | None = None
    # Kept for backward compatibility — maps to source_id when source_type=meeting
    meeting_id: uuid.UUID | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResultItem(BaseModel):
    # Polymorphic source info
    source_type: str = "meeting"
    source_id: uuid.UUID | None = None
    source_title: str | None = None
    # Backward-compat meeting fields (populated for meeting results)
    meeting_id: uuid.UUID | None = None
    meeting_title: str | None = None
    chunk_text: str
    similarity_score: float
    timestamp_start: float | None = None


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    query: str


class QARequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    # Polymorphic scope
    source_type: str | None = None
    source_id: uuid.UUID | None = None
    # Backward-compat
    meeting_id: uuid.UUID | None = None


class QAResponse(BaseModel):
    answer: str
    sources: list[SearchResultItem]
    model: str


# ── Incident Schemas ─────────────────────────────────────────────────────


class IncidentCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    severity: str = Field(default="sev3", pattern="^sev[1-4]$")
    status: str = Field(default="open")
    services_affected: list[str] = []
    description: str | None = None
    occurred_at: datetime | None = None


class IncidentUploadResponse(BaseModel):
    id: uuid.UUID
    title: str
    processing_status: str
    file_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class IncidentTimelineEventSchema(BaseModel):
    id: uuid.UUID | None = None
    event_index: int
    occurred_at: datetime | None = None
    description: str
    event_type: str = "event"

    model_config = {"from_attributes": True}


class IncidentActionItemSchema(BaseModel):
    id: uuid.UUID | None = None
    description: str
    assignee: str | None = None
    due_date: datetime | None = None
    priority: str = "medium"
    status: str = "open"
    category: str | None = None

    model_config = {"from_attributes": True}


class IncidentPostmortemSchema(BaseModel):
    executive_summary: str | None = None
    root_cause_analysis: str | None = None
    model_used: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class IncidentListItem(BaseModel):
    id: uuid.UUID
    title: str
    severity: str
    status: str
    processing_status: str
    services_affected: list[str] = []
    occurred_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class IncidentListResponse(BaseModel):
    items: list[IncidentListItem]
    total: int
    page: int
    page_size: int


class IncidentDetail(BaseModel):
    id: uuid.UUID
    title: str
    severity: str
    status: str
    processing_status: str
    services_affected: list[str] = []
    description: str | None = None
    raw_text: str | None = None
    file_name: str | None = None
    error_message: str | None = None
    occurred_at: datetime | None = None
    resolved_at: datetime | None = None
    postmortem: IncidentPostmortemSchema | None = None
    timeline: list[IncidentTimelineEventSchema] = []
    action_items: list[IncidentActionItemSchema] = []
    airtable_record_id: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class IncidentStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="New incident status (open, mitigated, resolved, closed)")
    resolved_at: datetime | None = None


class AirtableSyncResponse(BaseModel):
    airtable_record_id: str | None
    synced: bool


# ── Document Schemas ─────────────────────────────────────────────────────


class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    title: str
    processing_status: str
    file_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentListItem(BaseModel):
    id: uuid.UUID
    title: str
    doc_type: str
    processing_status: str
    file_name: str | None = None
    file_size_bytes: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentListItem]
    total: int
    page: int
    page_size: int


class DocumentDetail(BaseModel):
    id: uuid.UUID
    title: str
    doc_type: str
    processing_status: str
    file_name: str | None = None
    file_size_bytes: int | None = None
    content: str | None = None
    error_message: str | None = None
    airtable_record_id: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
