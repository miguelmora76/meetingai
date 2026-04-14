"""
SQLAlchemy ORM models for the MeetingAI database.

Tables:
    meetings                 — uploaded meeting recordings and their processing status
    transcripts              — full transcript text per meeting
    transcript_segments      — timestamped segments within a transcript
    summaries                — LLM-generated meeting summaries
    action_items             — extracted action items with assignees
    decisions                — extracted decisions with rationale
    embedding_chunks         — transcript chunks with vector embeddings for RAG
    incidents                — production incidents with description/file input
    incident_postmortems     — LLM-generated postmortem (exec summary + RCA)
    incident_timeline_events — ordered timeline of what happened
    incident_action_items    — remediation action items per incident
    incident_chunks          — incident text chunks with vector embeddings for RAG
    documents                — architecture / knowledge base documents
    doc_chunks               — document chunks with vector embeddings for RAG
"""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    date = Column(DateTime(timezone=True), default=datetime.utcnow)
    participants = Column(ARRAY(String), default=list)
    file_path = Column(String(1000), nullable=True)
    file_name = Column(String(500))
    file_size_bytes = Column(BigInteger)
    duration_seconds = Column(Integer)
    status = Column(String(50), nullable=False, default="uploaded")
    error_message = Column(Text)
    airtable_record_id = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    transcript = relationship("Transcript", back_populates="meeting", uselist=False, cascade="all, delete-orphan")
    summary = relationship("Summary", back_populates="meeting", uselist=False, cascade="all, delete-orphan")
    action_items = relationship("ActionItem", back_populates="meeting", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="meeting", cascade="all, delete-orphan")
    embedding_chunks = relationship("EmbeddingChunk", back_populates="meeting", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_meetings_status", "status"),
        Index("idx_meetings_date", "date"),
    )


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, unique=True)
    full_text = Column(Text, nullable=False)
    language = Column(String(10), default="en")
    word_count = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    meeting = relationship("Meeting", back_populates="transcript")
    segments = relationship("TranscriptSegment", back_populates="transcript", cascade="all, delete-orphan",
                            order_by="TranscriptSegment.segment_index")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transcript_id = Column(UUID(as_uuid=True), ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False)
    segment_index = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    speaker = Column(String(200))
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    transcript = relationship("Transcript", back_populates="segments")

    __table_args__ = (
        Index("idx_segments_transcript", "transcript_id", "segment_index"),
    )


class Summary(Base):
    __tablename__ = "summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, unique=True)
    content = Column(Text, nullable=False)
    model_used = Column(String(200))
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    meeting = relationship("Meeting", back_populates="summary")


class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    description = Column(Text, nullable=False)
    assignee = Column(String(200))
    due_date = Column(DateTime)
    priority = Column(String(20), default="medium")
    status = Column(String(20), default="open")
    source_quote = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    meeting = relationship("Meeting", back_populates="action_items")

    __table_args__ = (
        Index("idx_action_items_meeting", "meeting_id"),
        Index("idx_action_items_assignee", "assignee"),
    )


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    description = Column(Text, nullable=False)
    participants = Column(ARRAY(String), default=list)
    rationale = Column(Text)
    source_quote = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    meeting = relationship("Meeting", back_populates="decisions")

    __table_args__ = (
        Index("idx_decisions_meeting", "meeting_id"),
    )


class EmbeddingChunk(Base):
    __tablename__ = "embedding_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    start_char = Column(Integer)
    end_char = Column(Integer)
    timestamp_start = Column(Float)
    timestamp_end = Column(Float)
    embedding = Column(Vector(384), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    meeting = relationship("Meeting", back_populates="embedding_chunks")

    __table_args__ = (
        Index("idx_chunks_meeting", "meeting_id"),
    )


# ── Incident Models ────────────────────────────────────────────────────────


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    severity = Column(String(20), nullable=False, default="sev3")
    status = Column(String(50), nullable=False, default="open")
    services_affected = Column(ARRAY(String), default=list)
    description = Column(Text)
    raw_text = Column(Text)
    file_path = Column(String(1000))
    file_name = Column(String(500))
    processing_status = Column(String(50), nullable=False, default="pending")
    error_message = Column(Text)
    occurred_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    airtable_record_id = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    postmortem = relationship("IncidentPostmortem", back_populates="incident", uselist=False, cascade="all, delete-orphan")
    timeline_events = relationship("IncidentTimelineEvent", back_populates="incident", cascade="all, delete-orphan",
                                   order_by="IncidentTimelineEvent.event_index")
    action_items = relationship("IncidentActionItem", back_populates="incident", cascade="all, delete-orphan")
    chunks = relationship("IncidentChunk", back_populates="incident", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_incidents_processing_status", "processing_status"),
        Index("idx_incidents_severity", "severity"),
        Index("idx_incidents_status", "status"),
    )


class IncidentPostmortem(Base):
    __tablename__ = "incident_postmortems"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, unique=True)
    executive_summary = Column(Text)
    root_cause_analysis = Column(Text)
    model_used = Column(String(200))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    incident = relationship("Incident", back_populates="postmortem")

    __table_args__ = (
        Index("idx_postmortems_incident", "incident_id"),
    )


class IncidentTimelineEvent(Base):
    __tablename__ = "incident_timeline_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    event_index = Column(Integer, nullable=False)
    occurred_at = Column(DateTime(timezone=True))
    description = Column(Text, nullable=False)
    event_type = Column(String(50), default="event")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    incident = relationship("Incident", back_populates="timeline_events")

    __table_args__ = (
        Index("idx_timeline_incident", "incident_id", "event_index"),
    )


class IncidentActionItem(Base):
    __tablename__ = "incident_action_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    description = Column(Text, nullable=False)
    assignee = Column(String(200))
    due_date = Column(DateTime)
    priority = Column(String(20), default="medium")
    status = Column(String(20), default="open")
    category = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    incident = relationship("Incident", back_populates="action_items")

    __table_args__ = (
        Index("idx_incident_action_items_incident", "incident_id"),
    )


class IncidentChunk(Base):
    __tablename__ = "incident_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    start_char = Column(Integer)
    end_char = Column(Integer)
    embedding = Column(Vector(384), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    incident = relationship("Incident", back_populates="chunks")

    __table_args__ = (
        Index("idx_incident_chunks_incident", "incident_id"),
    )


# ── Document Models ────────────────────────────────────────────────────────


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    doc_type = Column(String(100), default="architecture")
    file_path = Column(String(1000))
    file_name = Column(String(500))
    file_size_bytes = Column(BigInteger)
    content = Column(Text)
    processing_status = Column(String(50), nullable=False, default="pending")
    error_message = Column(Text)
    airtable_record_id = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    chunks = relationship("DocChunk", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_documents_processing_status", "processing_status"),
        Index("idx_documents_doc_type", "doc_type"),
    )


class DocChunk(Base):
    __tablename__ = "doc_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    start_char = Column(Integer)
    end_char = Column(Integer)
    embedding = Column(Vector(384), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("idx_doc_chunks_document", "document_id"),
    )
