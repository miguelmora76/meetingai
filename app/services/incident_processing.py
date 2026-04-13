"""
Incident processing orchestrator — runs the full incident analysis pipeline.

Pipeline:
  1. Extract text (from raw_text or uploaded file)
  2. Generate postmortem (exec summary + RCA) concurrently with timeline + action items
  3. Embed incident text for RAG
"""

import asyncio
import logging
import uuid

from app.config.settings import Settings, get_settings
from app.db.repository import IncidentRepository
from app.llm.client import LLMClient
from app.rag.chunker import TranscriptChunker
from app.services.airtable_sync import AirtableSyncService
from app.services.incident_extraction import IncidentExtractionService

logger = logging.getLogger(__name__)


class IncidentProcessingService:
    """Orchestrates the full incident analysis pipeline."""

    def __init__(
        self,
        incident_repo: IncidentRepository,
        llm_client: LLMClient,
        settings: Settings | None = None,
    ):
        self.repo = incident_repo
        self.settings = settings or get_settings()
        self.extraction = IncidentExtractionService(llm_client, self.settings)
        self.llm = llm_client
        self.airtable = AirtableSyncService(self.settings)

    async def process_incident(self, incident_id: uuid.UUID) -> None:
        """
        Run the full analysis pipeline for an incident.

        On failure the processing_status is set to "failed" with an error message.
        """
        try:
            incident = await self.repo.get_incident(incident_id)
            if not incident:
                logger.error(f"Incident {incident_id} not found")
                return

            # Resolve text to analyse
            incident_text = incident.raw_text or incident.description or ""
            if not incident_text and incident.file_path:
                incident_text = await self._read_file(incident.file_path)

            if not incident_text.strip():
                await self.repo.update_incident_processing_status(
                    incident_id, "failed", error_message="No text content to analyse"
                )
                return

            await self.repo.update_incident_processing_status(incident_id, "analyzing")

            # ── Concurrent: postmortem + timeline + action items ──────────
            logger.info(f"[{incident_id}] Extracting postmortem, timeline, and action items...")

            exec_summary_rca, timeline_events = await asyncio.gather(
                self.extraction.generate_postmortem(
                    incident_text=incident_text,
                    title=incident.title,
                    severity=incident.severity,
                    services=incident.services_affected or [],
                ),
                self.extraction.extract_timeline(incident_text),
            )
            exec_summary, rca = exec_summary_rca

            # Extract action items with RCA context
            action_items = await self.extraction.extract_action_items(incident_text, rca)

            await self.repo.save_postmortem(
                incident_id=incident_id,
                executive_summary=exec_summary,
                root_cause_analysis=rca,
                model_used=self.settings.summarization_model,
            )
            await self.repo.save_timeline_events(incident_id, timeline_events)
            await self.repo.save_incident_action_items(incident_id, action_items)

            # ── Embed for RAG ─────────────────────────────────────────────
            logger.info(f"[{incident_id}] Generating embeddings...")
            await self.repo.update_incident_processing_status(incident_id, "embedding")
            chunk_count = await self._embed_incident(incident_id, incident_text)

            await self.repo.update_incident_processing_status(incident_id, "completed")

            # ── Airtable sync (non-blocking; failure is logged, not raised) ──
            airtable_record_id = await self.airtable.push_incident(
                incident_id=incident_id,
                title=incident.title,
                severity=incident.severity,
                status=incident.status,
                services_affected=incident.services_affected or [],
                executive_summary=exec_summary,
                root_cause_analysis=rca,
                action_items=[
                    {"description": a["description"], "assignee": a.get("assignee"), "priority": a.get("priority", "medium")}
                    for a in action_items
                ],
                occurred_at=incident.occurred_at,
                existing_record_id=incident.airtable_record_id,
            )
            if airtable_record_id:
                await self.repo.update_incident_airtable_id(incident_id, airtable_record_id)

            logger.info(
                f"[{incident_id}] Processing complete: "
                f"{len(timeline_events)} timeline events, {len(action_items)} action items, "
                f"{chunk_count} chunks embedded"
            )

        except Exception as e:
            logger.exception(f"[{incident_id}] Processing failed: {e}")
            await self.repo.update_incident_processing_status(
                incident_id, "failed", error_message=str(e)
            )
            raise

    async def _embed_incident(self, incident_id: uuid.UUID, text: str) -> int:
        chunker = TranscriptChunker(
            chunk_size=self.settings.chunk_size,
            overlap=self.settings.chunk_overlap,
        )
        chunks = chunker.chunk(text)
        if not chunks:
            return 0

        texts = [c.text for c in chunks]
        embeddings = await self.llm.embed(texts)

        for chunk, embedding in zip(chunks, embeddings):
            await self.repo.save_incident_chunk(
                incident_id=incident_id,
                chunk_index=chunk.index,
                chunk_text=chunk.text,
                embedding=embedding,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
            )

        return len(chunks)

    @staticmethod
    async def _read_file(file_path: str) -> str:
        """Read text content from an uploaded file (plain text, markdown, log files)."""
        def _read() -> str:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        try:
            return await asyncio.to_thread(_read)
        except Exception as e:
            logger.warning(f"Could not read file {file_path}: {e}")
            return ""
