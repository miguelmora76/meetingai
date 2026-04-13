"""
Vector retriever — performs similarity search against pgvector.

VectorRetriever: meeting-only (backward-compat)
PolymorphicRetriever: meetings + incidents + docs
"""

import logging
import uuid
from dataclasses import dataclass

from app.db.repository import MeetingRepository
from app.llm.client import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    meeting_id: uuid.UUID | None
    meeting_title: str | None
    chunk_text: str
    similarity_score: float
    timestamp_start: float | None = None
    source_type: str = "meeting"
    source_id: uuid.UUID | None = None
    source_title: str | None = None


class VectorRetriever:
    """Retrieves relevant transcript chunks via cosine similarity search (meetings only)."""

    def __init__(self, llm_client: LLMClient, repo: MeetingRepository):
        self.llm = llm_client
        self.repo = repo

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        meeting_id: uuid.UUID | None = None,
    ) -> list[RetrievedChunk]:
        logger.info(f"Retrieving top {top_k} chunks for query: {query[:100]}...")

        embeddings = await self.llm.embed([query])
        query_embedding = embeddings[0]

        results = await self.repo.search_embeddings(
            query_embedding=query_embedding,
            top_k=top_k,
            meeting_id=meeting_id,
        )

        chunks = [
            RetrievedChunk(
                meeting_id=r["meeting_id"],
                meeting_title=r["meeting_title"],
                chunk_text=r["chunk_text"],
                similarity_score=r["similarity_score"],
                timestamp_start=r["timestamp_start"],
                source_type="meeting",
                source_id=r["meeting_id"],
                source_title=r["meeting_title"],
            )
            for r in results
        ]

        logger.info(f"Retrieved {len(chunks)} chunks (top score: {chunks[0].similarity_score if chunks else 'N/A'})")
        return chunks


class PolymorphicRetriever:
    """Retrieves chunks from meetings, incidents, and knowledge-base documents."""

    def __init__(self, llm_client: LLMClient, repo: MeetingRepository):
        self.llm = llm_client
        self.repo = repo

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        source_type: str | None = None,
        source_id: uuid.UUID | None = None,
    ) -> list[RetrievedChunk]:
        logger.info(
            f"Polymorphic retrieve top {top_k} chunks (source_type={source_type}, "
            f"source_id={source_id}) for query: {query[:100]}..."
        )

        embeddings = await self.llm.embed([query])
        query_embedding = embeddings[0]

        results = await self.repo.search_all_embeddings(
            query_embedding=query_embedding,
            top_k=top_k,
            source_type=source_type,
            source_id=source_id,
        )

        chunks = [
            RetrievedChunk(
                meeting_id=r.get("meeting_id"),
                meeting_title=r.get("meeting_title"),
                chunk_text=r["chunk_text"],
                similarity_score=r["similarity_score"],
                timestamp_start=r.get("timestamp_start"),
                source_type=r["source_type"],
                source_id=r["source_id"],
                source_title=r["source_title"],
            )
            for r in results
        ]

        logger.info(f"Retrieved {len(chunks)} chunks (top score: {chunks[0].similarity_score if chunks else 'N/A'})")
        return chunks
