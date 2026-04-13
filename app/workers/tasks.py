"""
Background task definitions.

These run inside FastAPI's BackgroundTasks — no external queue needed for POC.
Each task is wrapped in asyncio.wait_for() so runaway processing jobs time out
instead of hanging indefinitely. Failures always update the DB status record.
"""

import asyncio
import logging
import time
import uuid

from prometheus_client import Counter, Histogram

from app.config.settings import get_settings
from app.db.repository import DocumentRepository, IncidentRepository, MeetingRepository
from app.db.session import AsyncSessionLocal
from app.llm.client import LLMClient
from app.services.doc_processing import DocProcessingService
from app.services.incident_processing import IncidentProcessingService
from app.services.processing import ProcessingService
from app.slack.factory import create_slack_client

# Custom processing metrics
meeting_processing_total = Counter(
    "meeting_processing_total",
    "Total number of meeting processing jobs",
    ["status"],
)
meeting_processing_duration = Histogram(
    "meeting_processing_duration_seconds",
    "Time spent processing a meeting (transcription through embedding)",
)

logger = logging.getLogger(__name__)


async def process_meeting_task(meeting_id: uuid.UUID) -> None:
    """
    Background task that runs the full meeting processing pipeline.

    Creates its own database session since it runs outside the request lifecycle.
    Times out after settings.processing_timeout_seconds (default 30 min).
    """
    logger.info(f"Background task started for meeting {meeting_id}")
    settings = get_settings()
    start_time = time.monotonic()

    async def _run() -> None:
        async with AsyncSessionLocal() as session:
            repo = MeetingRepository(session)
            llm_client = LLMClient()
            slack_client = create_slack_client()

            service = ProcessingService(
                repo=repo,
                llm_client=llm_client,
                slack_client=slack_client,
            )
            await service.process_meeting(meeting_id)

    try:
        await asyncio.wait_for(_run(), timeout=settings.processing_timeout_seconds)
        duration = time.monotonic() - start_time
        meeting_processing_duration.observe(duration)
        meeting_processing_total.labels(status="success").inc()
        logger.info(f"Background task completed for meeting {meeting_id} in {duration:.1f}s")
    except asyncio.TimeoutError:
        meeting_processing_total.labels(status="timeout").inc()
        logger.error(
            f"Background task timed out for meeting {meeting_id} "
            f"(limit: {settings.processing_timeout_seconds}s)"
        )
        async with AsyncSessionLocal() as session:
            await MeetingRepository(session).update_meeting_status(
                meeting_id, "failed", error_message="Processing timed out"
            )
    except Exception as e:
        meeting_processing_total.labels(status="failed").inc()
        logger.exception(f"Background task failed for meeting {meeting_id}: {e}")
        async with AsyncSessionLocal() as session:
            await MeetingRepository(session).update_meeting_status(
                meeting_id, "failed", error_message=str(e)[:1000]
            )


async def process_incident_task(incident_id: uuid.UUID, notify_channel: str | None = None) -> None:
    """Background task that runs the full incident analysis pipeline."""
    logger.info(f"Background task started for incident {incident_id}")
    settings = get_settings()
    slack_client = create_slack_client()

    async def _run() -> None:
        async with AsyncSessionLocal() as session:
            repo = IncidentRepository(session)
            llm_client = LLMClient()

            service = IncidentProcessingService(
                incident_repo=repo,
                llm_client=llm_client,
            )
            await service.process_incident(incident_id)

    try:
        await asyncio.wait_for(_run(), timeout=settings.processing_timeout_seconds)
        logger.info(f"Background task completed for incident {incident_id}")
    except asyncio.TimeoutError:
        logger.error(f"Background task timed out for incident {incident_id}")
        async with AsyncSessionLocal() as session:
            await IncidentRepository(session).update_incident_processing_status(
                incident_id, "failed", error_message="Processing timed out"
            )
        return
    except Exception as e:
        logger.exception(f"Background task failed for incident {incident_id}: {e}")
        async with AsyncSessionLocal() as session:
            await IncidentRepository(session).update_incident_processing_status(
                incident_id, "failed", error_message=str(e)[:1000]
            )
        return

    # Notify Slack (channel comes from default config when not triggered by bot)
    try:
        async with AsyncSessionLocal() as session:
            repo = IncidentRepository(session)
            incident = await repo.get_incident(incident_id)
        if incident:
            await slack_client.notify_incident_complete(incident, channel=notify_channel)
    except Exception:
        logger.exception(f"Slack notification failed for incident {incident_id}")


async def process_document_task(document_id: uuid.UUID) -> None:
    """Background task that embeds a knowledge-base document for RAG."""
    logger.info(f"Background task started for document {document_id}")
    settings = get_settings()

    async def _run() -> None:
        async with AsyncSessionLocal() as session:
            repo = DocumentRepository(session)
            llm_client = LLMClient()

            service = DocProcessingService(
                doc_repo=repo,
                llm_client=llm_client,
            )
            await service.process_document(document_id)

    try:
        await asyncio.wait_for(_run(), timeout=settings.processing_timeout_seconds)
        logger.info(f"Background task completed for document {document_id}")
    except asyncio.TimeoutError:
        logger.error(f"Background task timed out for document {document_id}")
        async with AsyncSessionLocal() as session:
            await DocumentRepository(session).update_document_processing_status(
                document_id, "failed", error_message="Processing timed out"
            )
    except Exception as e:
        logger.exception(f"Background task failed for document {document_id}: {e}")
        async with AsyncSessionLocal() as session:
            await DocumentRepository(session).update_document_processing_status(
                document_id, "failed", error_message=str(e)[:1000]
            )
