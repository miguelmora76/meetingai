"""
Background tasks that handle Slack bot interactions.

These run inside FastAPI's BackgroundTasks so that slash command handlers
can return HTTP 200 to Slack within the 3-second window, while the actual
work (LLM calls, DB queries) happens here asynchronously.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.db.repository import IncidentRepository, MeetingRepository
from app.db.session import AsyncSessionLocal
from app.llm.client import LLMClient
from app.rag.qa import RAGQueryService
from app.rag.retriever import PolymorphicRetriever
from app.services.incident_processing import IncidentProcessingService
from app.slack.factory import create_slack_client
from app.slack.message_builder import (
    error_message,
    incident_complete_message,
    incident_created_message,
    incident_list_message,
    meeting_list_message,
    qa_answer_message,
    search_results_message,
)

logger = logging.getLogger(__name__)


async def handle_slash_ask(
    question: str,
    channel: str,
    user_id: str,
    scope_type: str | None = None,
    scope_id: uuid.UUID | None = None,
    thread_ts: str | None = None,
) -> None:
    """Answer a RAG question and post the result to Slack."""
    slack = create_slack_client()
    try:
        async with AsyncSessionLocal() as session:
            repo = MeetingRepository(session)
            llm_client = LLMClient()
            retriever = PolymorphicRetriever(llm_client, repo)
            qa_service = RAGQueryService(llm_client, retriever)

            response = await qa_service.answer(
                question=question,
                source_type=scope_type,
                source_id=scope_id,
            )

        blocks = qa_answer_message(question, response.answer, response.sources)
        kwargs: dict[str, Any] = {"channel": channel, "text": response.answer[:200], "blocks": blocks}
        if thread_ts:
            kwargs["thread_ts"] = thread_ts
        await slack.post_message(**kwargs)

    except Exception:
        logger.exception("handle_slash_ask failed")
        await slack.post_message(
            channel=channel,
            text="Sorry, something went wrong answering your question.",
            blocks=error_message("Something went wrong answering your question. Please try again."),
        )


async def handle_slash_search(
    query: str,
    channel: str,
    user_id: str,
    scope_type: str | None = None,
    scope_id: uuid.UUID | None = None,
) -> None:
    """Run semantic search and post results to Slack."""
    slack = create_slack_client()
    try:
        async with AsyncSessionLocal() as session:
            repo = MeetingRepository(session)
            llm_client = LLMClient()
            retriever = PolymorphicRetriever(llm_client, repo)

            chunks = await retriever.retrieve(
                query=query,
                top_k=5,
                source_type=scope_type,
                source_id=scope_id,
            )

        blocks = search_results_message(query, chunks)
        await slack.post_message(channel=channel, text=f"Search results for: {query}", blocks=blocks)

    except Exception:
        logger.exception("handle_slash_search failed")
        await slack.post_message(
            channel=channel,
            text="Sorry, something went wrong with the search.",
            blocks=error_message("Search failed. Please try again."),
        )


async def handle_modal_log_incident(
    title: str,
    severity: str,
    status: str,
    services_affected: list[str],
    description: str,
    channel: str,
    user_id: str,
) -> None:
    """
    Create an incident from a submitted modal and kick off AI analysis.

    Posts an ephemeral ack immediately, then runs the processing pipeline
    and posts the full postmortem when done.
    """
    slack = create_slack_client()
    incident_id: uuid.UUID | None = None

    try:
        async with AsyncSessionLocal() as session:
            repo = IncidentRepository(session)
            incident = await repo.create_incident(
                title=title,
                severity=severity,
                status=status,
                services_affected=services_affected,
                description=description,
                raw_text=description,
            )
            incident_id = incident.id
            created_id = incident.id

        # Ack the user before analysis starts
        ack_blocks = incident_created_message(created_id, title, severity)
        await slack.post_message(
            channel=channel,
            text=f"Incident logged: {title}",
            blocks=ack_blocks,
        )

        # Run analysis in this same background task (it's already async)
        async with AsyncSessionLocal() as session:
            repo = IncidentRepository(session)
            llm_client = LLMClient()
            service = IncidentProcessingService(incident_repo=repo, llm_client=llm_client)
            await service.process_incident(created_id)

        # Post completed analysis
        await notify_incident_complete(created_id, channel)

    except Exception:
        logger.exception("handle_modal_log_incident failed")
        msg = "Incident analysis failed."
        if incident_id:
            msg = f"Incident was logged (id: `{str(incident_id)[:8]}`) but AI analysis failed."
        await slack.post_message(
            channel=channel,
            text=msg,
            blocks=error_message(msg),
        )


async def notify_incident_complete(incident_id: uuid.UUID, channel: str) -> None:
    """Fetch a completed incident and post its postmortem summary to Slack."""
    slack = create_slack_client()
    try:
        async with AsyncSessionLocal() as session:
            repo = IncidentRepository(session)
            incident = await repo.get_incident(incident_id)

        if not incident:
            logger.warning(f"notify_incident_complete: incident {incident_id} not found")
            return

        blocks = incident_complete_message(incident)
        await slack.post_message(
            channel=channel,
            text=f"Incident analysis complete: {incident.title}",
            blocks=blocks,
        )

    except Exception:
        logger.exception(f"notify_incident_complete failed for {incident_id}")


async def handle_list_incidents(channel: str) -> None:
    """Fetch 5 most recent incidents and post the list to Slack."""
    slack = create_slack_client()
    try:
        async with AsyncSessionLocal() as session:
            repo = IncidentRepository(session)
            incidents, _ = await repo.list_incidents(page=1, page_size=5)

        blocks = incident_list_message(incidents)
        await slack.post_message(channel=channel, text="Recent incidents", blocks=blocks)

    except Exception:
        logger.exception("handle_list_incidents failed")
        await slack.post_message(
            channel=channel,
            text="Could not fetch incidents.",
            blocks=error_message("Could not fetch incidents."),
        )


async def handle_list_meetings(channel: str) -> None:
    """Fetch 5 most recent meetings and post the list to Slack."""
    slack = create_slack_client()
    try:
        async with AsyncSessionLocal() as session:
            repo = MeetingRepository(session)
            meetings, _ = await repo.list_meetings(page=1, page_size=5)

        blocks = meeting_list_message(meetings)
        await slack.post_message(channel=channel, text="Recent meetings", blocks=blocks)

    except Exception:
        logger.exception("handle_list_meetings failed")
        await slack.post_message(
            channel=channel,
            text="Could not fetch meetings.",
            blocks=error_message("Could not fetch meetings."),
        )
