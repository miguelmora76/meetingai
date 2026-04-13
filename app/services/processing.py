"""
Processing orchestrator — runs the full meeting processing pipeline.

Pipeline: transcribe → summarize (concurrent) → embed → notify

Supports partial recovery: if a transcript already exists in the DB the
transcription step is skipped. This means a meeting that failed during
summarization can be re-queued without re-running expensive Whisper.
"""

import asyncio
import logging
import uuid

from app.config.settings import Settings, get_settings
from app.db.repository import MeetingRepository
from app.llm.client import LLMClient
from app.services.embedding import EmbeddingService
from app.services.summarization import SummarizationService
from app.services.transcription import TranscriptionService
from app.slack.base import SlackClient

logger = logging.getLogger(__name__)


class ProcessingService:
    """Orchestrates the full meeting processing pipeline."""

    def __init__(
        self,
        repo: MeetingRepository,
        llm_client: LLMClient,
        slack_client: SlackClient,
        settings: Settings | None = None,
    ):
        self.repo = repo
        self.settings = settings or get_settings()
        self.transcription = TranscriptionService(self.settings)
        self.summarization = SummarizationService(llm_client, self.settings)
        self.embedding = EmbeddingService(llm_client, repo, self.settings)
        self.slack = slack_client

    async def process_meeting(self, meeting_id: uuid.UUID) -> None:
        """
        Run the full processing pipeline for a meeting.

        Steps:
            1. Transcribe audio/video file (skipped if transcript already exists)
            2. Generate summary, extract action items, extract decisions (concurrent)
            3. Generate and store embeddings for RAG
            4. Send Slack notification

        On failure, the meeting status is set to "failed" with an error message.
        """
        try:
            meeting = await self.repo.get_meeting(meeting_id)
            if not meeting:
                logger.error(f"Meeting {meeting_id} not found")
                return

            participants_str = ", ".join(meeting.participants) if meeting.participants else "Unknown"
            date_str = meeting.date.strftime("%Y-%m-%d") if meeting.date else "Unknown"

            # ── Step 1: Transcribe (skip if already done) ─────────────────
            if meeting.transcript:
                logger.info(f"[{meeting_id}] Step 1/4: Transcript already exists, skipping.")
                full_text = meeting.transcript.full_text
                segments_data = [
                    {"start": seg.start_time, "end": seg.end_time, "text": seg.text, "speaker": seg.speaker}
                    for seg in (meeting.transcript.segments or [])
                ]
                duration_seconds = meeting.duration_seconds
            else:
                logger.info(f"[{meeting_id}] Step 1/4: Transcribing...")
                await self.repo.update_meeting_status(meeting_id, "transcribing")

                result = await self.transcription.transcribe(meeting.file_path)

                segments_data = [
                    {"start": s.start, "end": s.end, "text": s.text, "speaker": s.speaker}
                    for s in result.segments
                ]
                await self.repo.save_transcript(
                    meeting_id=meeting_id,
                    full_text=result.full_text,
                    segments=segments_data,
                    language=result.language,
                )
                full_text = result.full_text
                duration_seconds = result.duration_seconds

            await self.repo.update_meeting_status(
                meeting_id, "summarizing", duration_seconds=duration_seconds
            )

            # ── Step 2: Summarize + Extract (concurrent) ──────────────────
            logger.info(f"[{meeting_id}] Step 2/4: Summarizing and extracting...")

            summary, action_items, decisions = await asyncio.gather(
                self.summarization.generate_summary(
                    transcript=full_text,
                    title=meeting.title,
                    date=date_str,
                    participants=participants_str,
                ),
                self.summarization.extract_action_items(
                    transcript=full_text,
                    participants=participants_str,
                ),
                self.summarization.extract_decisions(
                    transcript=full_text,
                    participants=participants_str,
                ),
            )

            await self.repo.save_summary(
                meeting_id=meeting_id,
                content=summary,
                model_used=self.settings.summarization_model,
            )
            await self.repo.save_action_items(meeting_id, action_items)
            await self.repo.save_decisions(meeting_id, decisions)

            # ── Step 3: Embed for RAG ─────────────────────────────────────
            logger.info(f"[{meeting_id}] Step 3/4: Generating embeddings...")
            await self.repo.update_meeting_status(meeting_id, "embedding")
            chunk_count = await self.embedding.embed_transcript(meeting_id, full_text)

            # ── Step 4: Notify ────────────────────────────────────────────
            logger.info(f"[{meeting_id}] Step 4/4: Sending notifications...")
            await self.repo.update_meeting_status(meeting_id, "completed")
            await self.slack.notify_processing_complete(meeting)

            logger.info(
                f"[{meeting_id}] Processing complete: "
                f"{len(segments_data)} segments, {len(action_items)} action items, "
                f"{len(decisions)} decisions, {chunk_count} chunks embedded"
            )

        except Exception as e:
            logger.exception(f"[{meeting_id}] Processing failed: {e}")
            await self.repo.update_meeting_status(
                meeting_id, "failed", error_message=str(e)
            )
            raise
