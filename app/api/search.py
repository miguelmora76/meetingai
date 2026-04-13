"""
Search and Q&A API — semantic search across meetings, incidents, and docs with RAG Q&A.

Scope encoding (query params):
  source_type=meeting|incident|doc  (omit for all)
  source_id=<uuid>                  (scope to a single source)
"""

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import MeetingRepository
from app.db.session import get_db
from app.limiter import limiter
from app.llm.client import LLMClient
from app.models.schemas import (
    QARequest,
    QAResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from app.rag.qa import RAGQueryService
from app.rag.retriever import PolymorphicRetriever

logger = logging.getLogger(__name__)
router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
@limiter.limit("60/minute")
async def search_all(
    request: Request,
    body: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Semantic search across meetings, incidents, and knowledge-base documents."""
    repo = MeetingRepository(db)
    llm_client = LLMClient()
    retriever = PolymorphicRetriever(llm_client, repo)

    chunks = await retriever.retrieve(
        query=body.query,
        top_k=body.top_k,
        source_type=body.source_type,
        source_id=body.source_id,
    )

    results = [
        SearchResultItem(
            source_type=chunk.source_type,
            source_id=chunk.source_id,
            source_title=chunk.source_title,
            meeting_id=chunk.meeting_id,
            meeting_title=chunk.meeting_title,
            chunk_text=chunk.chunk_text,
            similarity_score=chunk.similarity_score,
            timestamp_start=chunk.timestamp_start,
        )
        for chunk in chunks
    ]

    return SearchResponse(results=results, query=body.query)


@router.post("/qa", response_model=QAResponse)
@limiter.limit("60/minute")
async def ask_question(
    request: Request,
    body: QARequest,
    db: AsyncSession = Depends(get_db),
):
    """Ask a question across meetings, incidents, and docs using RAG."""
    repo = MeetingRepository(db)
    llm_client = LLMClient()
    retriever = PolymorphicRetriever(llm_client, repo)
    qa_service = RAGQueryService(llm_client, retriever)

    response = await qa_service.answer(
        question=body.question,
        source_type=body.source_type,
        source_id=body.source_id,
    )

    return response
