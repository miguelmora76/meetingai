"""
Data access layer — all database operations encapsulated here.

No raw SQL in services or routes. This is the single source of truth
for how data is read and written.
"""

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.database import (
    ActionItem,
    Decision,
    DocChunk,
    Document,
    EmbeddingChunk,
    Incident,
    IncidentActionItem,
    IncidentChunk,
    IncidentPostmortem,
    IncidentTimelineEvent,
    Meeting,
    Summary,
    Transcript,
    TranscriptSegment,
)


class MeetingRepository:
    """Data access operations for meetings and related entities."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Meetings ──────────────────────────────────────────────────────

    async def create_meeting(
        self,
        title: str,
        file_path: str | None = None,
        file_name: str | None = None,
        file_size_bytes: int | None = None,
        date: datetime | None = None,
        participants: list[str] | None = None,
        status: str = "uploaded",
    ) -> Meeting:
        meeting = Meeting(
            title=title,
            file_path=file_path,
            file_name=file_name,
            file_size_bytes=file_size_bytes,
            date=date or datetime.utcnow(),
            participants=participants or [],
            status=status,
        )
        self.db.add(meeting)
        await self.db.commit()
        await self.db.refresh(meeting)
        return meeting

    async def update_meeting_airtable_id(
        self, meeting_id: uuid.UUID, airtable_record_id: str
    ) -> None:
        result = await self.db.execute(select(Meeting).where(Meeting.id == meeting_id))
        meeting = result.scalar_one_or_none()
        if meeting:
            meeting.airtable_record_id = airtable_record_id
            meeting.updated_at = datetime.utcnow()
            await self.db.commit()

    async def update_meeting_file_path(self, meeting_id: uuid.UUID, file_path: str) -> None:
        result = await self.db.execute(select(Meeting).where(Meeting.id == meeting_id))
        meeting = result.scalar_one_or_none()
        if meeting:
            meeting.file_path = file_path
            meeting.updated_at = datetime.utcnow()
            await self.db.commit()

    async def get_meeting(self, meeting_id: uuid.UUID) -> Meeting | None:
        """Get a meeting with all related data eagerly loaded."""
        result = await self.db.execute(
            select(Meeting)
            .options(
                selectinload(Meeting.transcript).selectinload(Transcript.segments),
                selectinload(Meeting.summary),
                selectinload(Meeting.action_items),
                selectinload(Meeting.decisions),
            )
            .where(Meeting.id == meeting_id)
        )
        return result.scalar_one_or_none()

    async def list_meetings(
        self, page: int = 1, page_size: int = 20, status: str | None = None
    ) -> tuple[list[Meeting], int]:
        """Return paginated meeting list and total count."""
        query = select(Meeting).order_by(Meeting.date.desc())
        count_query = select(func.count(Meeting.id))

        if status:
            query = query.where(Meeting.status == status)
            count_query = count_query.where(Meeting.status == status)

        # Total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Paginated results
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        result = await self.db.execute(query)
        meetings = list(result.scalars().all())

        return meetings, total

    async def update_meeting_status(
        self,
        meeting_id: uuid.UUID,
        status: str,
        error_message: str | None = None,
        duration_seconds: int | None = None,
    ) -> None:
        result = await self.db.execute(
            select(Meeting).where(Meeting.id == meeting_id)
        )
        meeting = result.scalar_one_or_none()
        if meeting:
            meeting.status = status
            meeting.updated_at = datetime.utcnow()
            if error_message is not None:
                meeting.error_message = error_message
            if duration_seconds is not None:
                meeting.duration_seconds = duration_seconds
            await self.db.commit()

    # ── Transcripts ───────────────────────────────────────────────────

    async def save_transcript(
        self,
        meeting_id: uuid.UUID,
        full_text: str,
        segments: list[dict],
        language: str = "en",
    ) -> Transcript:
        """Save transcript and its segments."""
        word_count = len(full_text.split())
        transcript = Transcript(
            meeting_id=meeting_id,
            full_text=full_text,
            language=language,
            word_count=word_count,
        )
        self.db.add(transcript)
        await self.db.flush()  # get transcript.id

        for i, seg in enumerate(segments):
            segment = TranscriptSegment(
                transcript_id=transcript.id,
                segment_index=i,
                start_time=seg["start"],
                end_time=seg["end"],
                speaker=seg.get("speaker"),
                text=seg["text"],
            )
            self.db.add(segment)

        await self.db.commit()
        await self.db.refresh(transcript)
        return transcript

    # ── Summaries ─────────────────────────────────────────────────────

    async def save_summary(
        self,
        meeting_id: uuid.UUID,
        content: str,
        model_used: str | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
    ) -> Summary:
        summary = Summary(
            meeting_id=meeting_id,
            content=content,
            model_used=model_used,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        self.db.add(summary)
        await self.db.commit()
        await self.db.refresh(summary)
        return summary

    # ── Action Items ──────────────────────────────────────────────────

    async def save_action_items(
        self, meeting_id: uuid.UUID, items: list[dict]
    ) -> list[ActionItem]:
        action_items = []
        for item_data in items:
            action_item = ActionItem(
                meeting_id=meeting_id,
                description=item_data["description"],
                assignee=item_data.get("assignee"),
                due_date=item_data.get("due_date"),
                priority=item_data.get("priority", "medium"),
                source_quote=item_data.get("source_quote"),
            )
            self.db.add(action_item)
            action_items.append(action_item)
        await self.db.commit()
        return action_items

    # ── Decisions ─────────────────────────────────────────────────────

    async def save_decisions(
        self, meeting_id: uuid.UUID, decisions: list[dict]
    ) -> list[Decision]:
        decision_objs = []
        for dec_data in decisions:
            decision = Decision(
                meeting_id=meeting_id,
                description=dec_data["description"],
                participants=dec_data.get("participants", []),
                rationale=dec_data.get("rationale"),
                source_quote=dec_data.get("source_quote"),
            )
            self.db.add(decision)
            decision_objs.append(decision)
        await self.db.commit()
        return decision_objs

    # ── Embedding Chunks ──────────────────────────────────────────────

    async def save_embedding_chunk(
        self,
        meeting_id: uuid.UUID,
        chunk_index: int,
        chunk_text: str,
        embedding: list[float],
        start_char: int | None = None,
        end_char: int | None = None,
        timestamp_start: float | None = None,
        timestamp_end: float | None = None,
    ) -> EmbeddingChunk:
        chunk = EmbeddingChunk(
            meeting_id=meeting_id,
            chunk_index=chunk_index,
            chunk_text=chunk_text,
            embedding=embedding,
            start_char=start_char,
            end_char=end_char,
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
        )
        self.db.add(chunk)
        await self.db.commit()
        return chunk

    async def search_embeddings(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        meeting_id: uuid.UUID | None = None,
    ) -> list[dict]:
        """Cosine similarity search against embedding_chunks."""
        query = (
            select(
                EmbeddingChunk,
                Meeting.title.label("meeting_title"),
                EmbeddingChunk.embedding.cosine_distance(query_embedding).label("distance"),
            )
            .join(Meeting, EmbeddingChunk.meeting_id == Meeting.id)
            .order_by("distance")
            .limit(top_k)
        )
        if meeting_id:
            query = query.where(EmbeddingChunk.meeting_id == meeting_id)

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "meeting_id": row.EmbeddingChunk.meeting_id,
                "meeting_title": row.meeting_title,
                "chunk_text": row.EmbeddingChunk.chunk_text,
                "similarity_score": round(1 - row.distance, 4),
                "timestamp_start": row.EmbeddingChunk.timestamp_start,
            }
            for row in rows
        ]

    async def search_all_embeddings(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        source_type: str | None = None,
        source_id: uuid.UUID | None = None,
    ) -> list[dict]:
        """
        Polymorphic cosine similarity search across meeting, incident, and doc chunks.

        source_type: 'meeting' | 'incident' | 'doc' | None (all)
        source_id:   optional UUID to scope to a single source
        """
        results: list[dict] = []

        async def _search_meetings() -> list[dict]:
            q = (
                select(
                    EmbeddingChunk,
                    Meeting.title.label("source_title"),
                    EmbeddingChunk.embedding.cosine_distance(query_embedding).label("distance"),
                )
                .join(Meeting, EmbeddingChunk.meeting_id == Meeting.id)
                .order_by("distance")
                .limit(top_k)
            )
            if source_id:
                q = q.where(EmbeddingChunk.meeting_id == source_id)
            rows = (await self.db.execute(q)).all()
            return [
                {
                    "source_type": "meeting",
                    "source_id": row.EmbeddingChunk.meeting_id,
                    "source_title": row.source_title,
                    "chunk_text": row.EmbeddingChunk.chunk_text,
                    "similarity_score": round(1 - row.distance, 4),
                    "timestamp_start": row.EmbeddingChunk.timestamp_start,
                    # backward-compat fields
                    "meeting_id": row.EmbeddingChunk.meeting_id,
                    "meeting_title": row.source_title,
                }
                for row in rows
            ]

        async def _search_incidents() -> list[dict]:
            q = (
                select(
                    IncidentChunk,
                    Incident.title.label("source_title"),
                    IncidentChunk.embedding.cosine_distance(query_embedding).label("distance"),
                )
                .join(Incident, IncidentChunk.incident_id == Incident.id)
                .order_by("distance")
                .limit(top_k)
            )
            if source_id:
                q = q.where(IncidentChunk.incident_id == source_id)
            rows = (await self.db.execute(q)).all()
            return [
                {
                    "source_type": "incident",
                    "source_id": row.IncidentChunk.incident_id,
                    "source_title": row.source_title,
                    "chunk_text": row.IncidentChunk.chunk_text,
                    "similarity_score": round(1 - row.distance, 4),
                    "timestamp_start": None,
                    "meeting_id": None,
                    "meeting_title": None,
                }
                for row in rows
            ]

        async def _search_docs() -> list[dict]:
            q = (
                select(
                    DocChunk,
                    Document.title.label("source_title"),
                    DocChunk.embedding.cosine_distance(query_embedding).label("distance"),
                )
                .join(Document, DocChunk.document_id == Document.id)
                .order_by("distance")
                .limit(top_k)
            )
            if source_id:
                q = q.where(DocChunk.document_id == source_id)
            rows = (await self.db.execute(q)).all()
            return [
                {
                    "source_type": "doc",
                    "source_id": row.DocChunk.document_id,
                    "source_title": row.source_title,
                    "chunk_text": row.DocChunk.chunk_text,
                    "similarity_score": round(1 - row.distance, 4),
                    "timestamp_start": None,
                    "meeting_id": None,
                    "meeting_title": None,
                }
                for row in rows
            ]

        if source_type == "meeting":
            results = await _search_meetings()
        elif source_type == "incident":
            results = await _search_incidents()
        elif source_type == "doc":
            results = await _search_docs()
        else:
            from asyncio import gather
            parts = await gather(_search_meetings(), _search_incidents(), _search_docs())
            for part in parts:
                results.extend(part)

        results.sort(key=lambda r: r["similarity_score"], reverse=True)
        return results[:top_k]


# ── Incident Repository ────────────────────────────────────────────────────


class IncidentRepository:
    """Data access operations for incidents and related entities."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_incident(
        self,
        title: str,
        severity: str = "sev3",
        status: str = "open",
        services_affected: list[str] | None = None,
        description: str | None = None,
        raw_text: str | None = None,
        file_path: str | None = None,
        file_name: str | None = None,
        occurred_at: datetime | None = None,
    ) -> Incident:
        incident = Incident(
            title=title,
            severity=severity,
            status=status,
            services_affected=services_affected or [],
            description=description,
            raw_text=raw_text,
            file_path=file_path,
            file_name=file_name,
            occurred_at=occurred_at,
            processing_status="pending",
        )
        self.db.add(incident)
        await self.db.commit()
        await self.db.refresh(incident)
        return incident

    async def get_incident(self, incident_id: uuid.UUID) -> Incident | None:
        result = await self.db.execute(
            select(Incident)
            .options(
                selectinload(Incident.postmortem),
                selectinload(Incident.timeline_events),
                selectinload(Incident.action_items),
            )
            .where(Incident.id == incident_id)
        )
        return result.scalar_one_or_none()

    async def list_incidents(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[Incident], int]:
        count_result = await self.db.execute(select(func.count(Incident.id)))
        total = count_result.scalar_one()

        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(Incident).order_by(Incident.created_at.desc()).offset(offset).limit(page_size)
        )
        return list(result.scalars().all()), total

    async def update_incident_processing_status(
        self, incident_id: uuid.UUID, processing_status: str, error_message: str | None = None
    ) -> None:
        result = await self.db.execute(select(Incident).where(Incident.id == incident_id))
        incident = result.scalar_one_or_none()
        if incident:
            incident.processing_status = processing_status
            incident.updated_at = datetime.utcnow()
            if error_message is not None:
                incident.error_message = error_message
            await self.db.commit()

    async def update_incident_airtable_id(
        self, incident_id: uuid.UUID, airtable_record_id: str
    ) -> None:
        result = await self.db.execute(select(Incident).where(Incident.id == incident_id))
        incident = result.scalar_one_or_none()
        if incident:
            incident.airtable_record_id = airtable_record_id
            incident.updated_at = datetime.utcnow()
            await self.db.commit()

    async def update_incident_status(
        self,
        incident_id: uuid.UUID,
        status: str,
        resolved_at: datetime | None = None,
    ) -> None:
        result = await self.db.execute(select(Incident).where(Incident.id == incident_id))
        incident = result.scalar_one_or_none()
        if incident:
            incident.status = status
            incident.updated_at = datetime.utcnow()
            if resolved_at is not None:
                incident.resolved_at = resolved_at
            await self.db.commit()

    async def save_postmortem(
        self,
        incident_id: uuid.UUID,
        executive_summary: str,
        root_cause_analysis: str,
        model_used: str | None = None,
    ) -> IncidentPostmortem:
        postmortem = IncidentPostmortem(
            incident_id=incident_id,
            executive_summary=executive_summary,
            root_cause_analysis=root_cause_analysis,
            model_used=model_used,
        )
        self.db.add(postmortem)
        await self.db.commit()
        await self.db.refresh(postmortem)
        return postmortem

    async def save_timeline_events(
        self, incident_id: uuid.UUID, events: list[dict]
    ) -> list[IncidentTimelineEvent]:
        objs = []
        for i, ev in enumerate(events):
            obj = IncidentTimelineEvent(
                incident_id=incident_id,
                event_index=i,
                occurred_at=ev.get("occurred_at"),
                description=ev["description"],
                event_type=ev.get("event_type", "event"),
            )
            self.db.add(obj)
            objs.append(obj)
        await self.db.commit()
        return objs

    async def save_incident_action_items(
        self, incident_id: uuid.UUID, items: list[dict]
    ) -> list[IncidentActionItem]:
        objs = []
        for item_data in items:
            obj = IncidentActionItem(
                incident_id=incident_id,
                description=item_data["description"],
                assignee=item_data.get("assignee"),
                due_date=item_data.get("due_date"),
                priority=item_data.get("priority", "medium"),
                category=item_data.get("category"),
            )
            self.db.add(obj)
            objs.append(obj)
        await self.db.commit()
        return objs

    async def save_incident_chunk(
        self,
        incident_id: uuid.UUID,
        chunk_index: int,
        chunk_text: str,
        embedding: list[float],
        start_char: int | None = None,
        end_char: int | None = None,
    ) -> IncidentChunk:
        chunk = IncidentChunk(
            incident_id=incident_id,
            chunk_index=chunk_index,
            chunk_text=chunk_text,
            embedding=embedding,
            start_char=start_char,
            end_char=end_char,
        )
        self.db.add(chunk)
        await self.db.commit()
        return chunk


# ── Document Repository ────────────────────────────────────────────────────


class DocumentRepository:
    """Data access operations for knowledge-base documents."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_document(
        self,
        title: str,
        doc_type: str = "architecture",
        file_path: str | None = None,
        file_name: str | None = None,
        file_size_bytes: int | None = None,
        content: str | None = None,
        airtable_source_ref: dict | None = None,
    ) -> Document:
        doc = Document(
            title=title,
            doc_type=doc_type,
            file_path=file_path,
            file_name=file_name,
            file_size_bytes=file_size_bytes,
            content=content,
            processing_status="pending",
            airtable_source_ref=airtable_source_ref,
        )
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def find_document_by_airtable_record(
        self, base_id: str, record_id: str
    ) -> Document | None:
        """Return an existing document that was previously imported from the given Airtable record."""
        result = await self.db.execute(
            select(Document).where(
                Document.airtable_source_ref.op("->>")("record_id") == record_id,
                Document.airtable_source_ref.op("->>")("base_id") == base_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_document(self, document_id: uuid.UUID) -> Document | None:
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def list_documents(
        self, page: int = 1, page_size: int = 50
    ) -> tuple[list[Document], int]:
        count_result = await self.db.execute(select(func.count(Document.id)))
        total = count_result.scalar_one()

        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(Document).order_by(Document.created_at.desc()).offset(offset).limit(page_size)
        )
        return list(result.scalars().all()), total

    async def update_document_processing_status(
        self, document_id: uuid.UUID, processing_status: str, error_message: str | None = None
    ) -> None:
        result = await self.db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if doc:
            doc.processing_status = processing_status
            doc.updated_at = datetime.utcnow()
            if error_message is not None:
                doc.error_message = error_message
            await self.db.commit()

    async def update_document_airtable_id(
        self, document_id: uuid.UUID, airtable_record_id: str
    ) -> None:
        result = await self.db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if doc:
            doc.airtable_record_id = airtable_record_id
            doc.updated_at = datetime.utcnow()
            await self.db.commit()

    async def save_doc_chunk(
        self,
        document_id: uuid.UUID,
        chunk_index: int,
        chunk_text: str,
        embedding: list[float],
        start_char: int | None = None,
        end_char: int | None = None,
    ) -> DocChunk:
        chunk = DocChunk(
            document_id=document_id,
            chunk_index=chunk_index,
            chunk_text=chunk_text,
            embedding=embedding,
            start_char=start_char,
            end_char=end_char,
        )
        self.db.add(chunk)
        await self.db.commit()
        return chunk
