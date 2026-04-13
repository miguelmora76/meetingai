"""
Embedding service — generates and stores vector embeddings for transcript chunks.

Uses the chunker to split transcripts, then batches embedding API calls,
and stores results in pgvector via the repository.
"""

import logging
import uuid

from app.config.settings import Settings, get_settings
from app.db.repository import MeetingRepository
from app.llm.client import LLMClient
from app.rag.chunker import Chunk, TranscriptChunker

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generates embeddings for transcript chunks and stores them in pgvector."""

    def __init__(
        self,
        llm_client: LLMClient,
        repo: MeetingRepository,
        settings: Settings | None = None,
    ):
        self.llm = llm_client
        self.repo = repo
        self.settings = settings or get_settings()
        self.chunker = TranscriptChunker(
            chunk_size=self.settings.chunk_size,
            overlap=self.settings.chunk_overlap,
        )

    async def embed_transcript(self, meeting_id: uuid.UUID, transcript: str) -> int:
        """
        Chunk a transcript, embed each chunk, and store in pgvector.

        Returns the number of chunks created.
        """
        chunks = self.chunker.chunk(transcript)
        logger.info(f"Chunked transcript into {len(chunks)} chunks for meeting {meeting_id}")

        if not chunks:
            return 0

        # Batch embed — OpenAI supports up to 2048 inputs per request
        batch_size = 100
        total_stored = 0

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            texts = [c.text for c in batch]

            embeddings = await self.llm.embed(texts)

            for chunk, embedding in zip(batch, embeddings):
                await self.repo.save_embedding_chunk(
                    meeting_id=meeting_id,
                    chunk_index=chunk.index,
                    chunk_text=chunk.text,
                    embedding=embedding,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                )
                total_stored += 1

        logger.info(f"Stored {total_stored} embedding chunks for meeting {meeting_id}")
        return total_stored
