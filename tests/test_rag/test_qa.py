"""Unit tests for RAGQueryService."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.llm.client import LLMClient
from app.rag.qa import RAGQueryService
from app.rag.retriever import PolymorphicRetriever, RetrievedChunk


def _make_chunk(text: str = "Some relevant content.") -> RetrievedChunk:
    return RetrievedChunk(
        meeting_id=uuid.uuid4(),
        meeting_title="Sprint Planning",
        chunk_text=text,
        similarity_score=0.85,
        source_type="meeting",
        source_id=uuid.uuid4(),
        source_title="Sprint Planning",
    )


@pytest.fixture
def mock_llm():
    llm = MagicMock(spec=LLMClient)
    llm.complete = AsyncMock(return_value="Here is the answer.")
    llm.embed = AsyncMock(return_value=[[0.1] * 384])
    return llm


@pytest.fixture
def make_qa_service(mock_llm):
    def _factory(chunks: list):
        retriever = MagicMock(spec=PolymorphicRetriever)
        retriever.retrieve = AsyncMock(return_value=chunks)
        return RAGQueryService(llm_client=mock_llm, retriever=retriever)

    return _factory


@pytest.mark.asyncio
async def test_answer_with_zero_chunks_returns_fallback(make_qa_service):
    """When no chunks are retrieved the service must return the no-results fallback."""
    service = make_qa_service(chunks=[])
    response = await service.answer("What was discussed?")
    assert "couldn't find" in response.answer.lower()
    assert response.sources == []


@pytest.mark.asyncio
async def test_answer_with_two_chunks_returns_two_sources(make_qa_service, mock_llm):
    """When two chunks are retrieved the response must include two source references."""
    chunks = [_make_chunk("First chunk."), _make_chunk("Second chunk.")]
    service = make_qa_service(chunks=chunks)
    response = await service.answer("What was decided?")
    assert len(response.sources) == 2
    mock_llm.complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_answer_passes_question_to_llm(make_qa_service, mock_llm):
    """The question must be included in the prompt sent to the LLM."""
    service = make_qa_service(chunks=[_make_chunk()])
    await service.answer("What are the action items?")
    call_kwargs = mock_llm.complete.call_args
    # The question should appear in either the system or user prompt
    all_text = " ".join(str(v) for v in call_kwargs.args) + str(call_kwargs.kwargs)
    assert "action items" in all_text.lower()
