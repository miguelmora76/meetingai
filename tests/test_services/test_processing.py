"""Unit tests for ProcessingService — pipeline orchestration."""

import uuid
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

from app.services.processing import ProcessingService
from app.services.transcription import TranscriptResult, TranscriptSegment


def _make_mock_meeting(meeting_id: uuid.UUID, has_transcript: bool = False):
    meeting = MagicMock()
    meeting.id = meeting_id
    meeting.title = "Test Meeting"
    meeting.date = None
    meeting.participants = ["Alice", "Bob"]
    meeting.file_path = "/tmp/fake.mp3"
    meeting.duration_seconds = None
    meeting.transcript = None

    if has_transcript:
        transcript = MagicMock()
        transcript.full_text = "Existing transcript text."
        segment = MagicMock()
        segment.start_time = 0.0
        segment.end_time = 5.0
        segment.text = "Hello"
        segment.speaker = None
        transcript.segments = [segment]
        meeting.transcript = transcript

    return meeting


@pytest.fixture
def make_service(mocker):
    """Return a factory that builds a ProcessingService with mocked dependencies."""

    def _factory():
        repo = MagicMock()
        repo.get_meeting = AsyncMock()
        repo.update_meeting_status = AsyncMock()
        repo.save_transcript = AsyncMock()
        repo.save_summary = AsyncMock()
        repo.save_action_items = AsyncMock()
        repo.save_decisions = AsyncMock()
        repo.update_meeting_file_path = AsyncMock()

        llm_client = MagicMock()
        slack_client = MagicMock()
        slack_client.notify_processing_complete = AsyncMock()

        service = ProcessingService(repo=repo, llm_client=llm_client, slack_client=slack_client)

        # Mock out the sub-services
        service.transcription = MagicMock()
        service.transcription.transcribe = AsyncMock(
            return_value=TranscriptResult(
                full_text="Hello world.",
                segments=[TranscriptSegment(start=0.0, end=2.0, text="Hello world.", speaker=None)],
                language="en",
                duration_seconds=2,
            )
        )
        service.summarization = MagicMock()
        service.summarization.generate_summary = AsyncMock(return_value="A great meeting.")
        service.summarization.extract_action_items = AsyncMock(
            return_value=[{"description": "Follow up", "assignee": "Alice"}]
        )
        service.summarization.extract_decisions = AsyncMock(
            return_value=[{"decision": "Use PostgreSQL", "rationale": "Reliability"}]
        )
        service.embedding = MagicMock()
        service.embedding.embed_transcript = AsyncMock(return_value=5)

        return service, repo

    return _factory


@pytest.mark.asyncio
async def test_process_meeting_calls_all_steps(make_service):
    """A fresh meeting should run all 4 pipeline steps."""
    meeting_id = uuid.uuid4()
    service, repo = make_service()
    meeting = _make_mock_meeting(meeting_id)
    repo.get_meeting.return_value = meeting

    await service.process_meeting(meeting_id)

    service.transcription.transcribe.assert_awaited_once()
    repo.save_transcript.assert_awaited_once()
    service.summarization.generate_summary.assert_awaited_once()
    repo.save_summary.assert_awaited_once()
    repo.save_action_items.assert_awaited_once()
    repo.save_decisions.assert_awaited_once()
    service.embedding.embed_transcript.assert_awaited_once()
    repo.update_meeting_status.assert_any_await(meeting_id, "completed")


@pytest.mark.asyncio
async def test_process_meeting_skips_transcription_when_transcript_exists(make_service):
    """If a transcript already exists, transcription must be skipped."""
    meeting_id = uuid.uuid4()
    service, repo = make_service()
    meeting = _make_mock_meeting(meeting_id, has_transcript=True)
    repo.get_meeting.return_value = meeting

    await service.process_meeting(meeting_id)

    service.transcription.transcribe.assert_not_awaited()
    repo.save_transcript.assert_not_awaited()
    # Summarization should still run
    service.summarization.generate_summary.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_meeting_sets_failed_on_llm_error(make_service):
    """If the LLM raises during summarization, the meeting must be marked failed."""
    import anthropic

    meeting_id = uuid.uuid4()
    service, repo = make_service()
    meeting = _make_mock_meeting(meeting_id)
    repo.get_meeting.return_value = meeting

    service.summarization.generate_summary.side_effect = anthropic.InternalServerError(
        message="server error",
        response=MagicMock(status_code=500),
        body={},
    )

    with pytest.raises(Exception):
        await service.process_meeting(meeting_id)

    repo.update_meeting_status.assert_any_await(meeting_id, "failed", error_message=ANY)


@pytest.mark.asyncio
async def test_process_meeting_not_found_returns_early(make_service):
    """If the meeting does not exist the pipeline must exit without error."""
    meeting_id = uuid.uuid4()
    service, repo = make_service()
    repo.get_meeting.return_value = None

    # Should not raise
    await service.process_meeting(meeting_id)

    service.transcription.transcribe.assert_not_awaited()
