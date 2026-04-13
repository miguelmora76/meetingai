"""
RAG question answering pipeline.

Flow: embed query → retrieve chunks → build context → prompt LLM → return answer.
"""

import logging
import uuid

from app.config.settings import Settings, get_settings
from app.llm.client import LLMClient
from app.llm.prompts import rag_qa_prompts
from app.models.schemas import QAResponse, SearchResultItem
from app.rag.retriever import PolymorphicRetriever, VectorRetriever

logger = logging.getLogger(__name__)


class RAGQueryService:
    """End-to-end RAG question answering across meetings."""

    def __init__(
        self,
        llm_client: LLMClient,
        retriever: VectorRetriever,
        settings: Settings | None = None,
    ):
        self.llm = llm_client
        self.retriever = retriever
        self.settings = settings or get_settings()

    async def answer(
        self,
        question: str,
        meeting_id: uuid.UUID | None = None,
        source_type: str | None = None,
        source_id: uuid.UUID | None = None,
    ) -> QAResponse:
        """
        Answer a question using RAG over meetings, incidents, and docs.

        meeting_id is kept for backward compatibility.
        """
        # Resolve backward-compat meeting_id
        if meeting_id and not source_id:
            source_type = "meeting"
            source_id = meeting_id

        # 1. Retrieve relevant chunks
        if isinstance(self.retriever, PolymorphicRetriever):
            chunks = await self.retriever.retrieve(
                query=question,
                top_k=self.settings.retrieval_top_k,
                source_type=source_type,
                source_id=source_id,
            )
        else:
            chunks = await self.retriever.retrieve(
                query=question,
                top_k=self.settings.retrieval_top_k,
                meeting_id=source_id,
            )

        if not chunks:
            return QAResponse(
                answer="I couldn't find any relevant meeting content to answer this question.",
                sources=[],
                model=self.settings.summarization_model,
            )

        # 2. Build context string with source labels
        context_parts = []
        for chunk in chunks:
            source_label = chunk.source_title or chunk.meeting_title or "Unknown"
            type_label = chunk.source_type.capitalize() if chunk.source_type else "Meeting"

            timestamp = ""
            if chunk.timestamp_start is not None:
                minutes = int(chunk.timestamp_start // 60)
                seconds = int(chunk.timestamp_start % 60)
                timestamp = f" | Timestamp: {minutes}:{seconds:02d}"

            context_parts.append(
                f'[{type_label}: {source_label}{timestamp}]\n"{chunk.chunk_text}"'
            )

        context_str = "\n\n".join(context_parts)

        # 3. Prompt LLM
        system, user = rag_qa_prompts(question, context_str)
        answer = await self.llm.complete(
            model=self.settings.summarization_model,
            system=system,
            user=user,
        )

        # 4. Build source references
        sources = [
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

        return QAResponse(
            answer=answer,
            sources=sources,
            model=self.settings.summarization_model,
        )
