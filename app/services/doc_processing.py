"""
Document processing service — ingests architecture / knowledge-base documents,
extracts text, and generates embeddings for RAG.

Supported file types: .txt, .md, .log, .yaml, .json, .py (anything text-based).
"""

import asyncio
import logging
import uuid

from app.config.settings import Settings, get_settings
from app.db.repository import DocumentRepository
from app.llm.client import LLMClient
from app.rag.chunker import TranscriptChunker

logger = logging.getLogger(__name__)


class DocProcessingService:
    """Reads a document file, chunks it, and stores embeddings."""

    def __init__(
        self,
        doc_repo: DocumentRepository,
        llm_client: LLMClient,
        settings: Settings | None = None,
    ):
        self.repo = doc_repo
        self.settings = settings or get_settings()
        self.llm = llm_client

    async def process_document(self, document_id: uuid.UUID) -> None:
        try:
            doc = await self.repo.get_document(document_id)
            if not doc:
                logger.error(f"Document {document_id} not found")
                return

            text = doc.content or ""
            if not text and doc.file_path:
                text = await self._read_file(doc.file_path)

            if not text.strip():
                await self.repo.update_document_processing_status(
                    document_id, "failed", error_message="No text content to embed"
                )
                return

            await self.repo.update_document_processing_status(document_id, "embedding")

            chunker = TranscriptChunker(
                chunk_size=self.settings.chunk_size,
                overlap=self.settings.chunk_overlap,
            )
            chunks = chunker.chunk(text)

            if not chunks:
                await self.repo.update_document_processing_status(
                    document_id, "failed", error_message="Text produced no chunks"
                )
                return

            texts = [c.text for c in chunks]
            embeddings = await self.llm.embed(texts)

            for chunk, embedding in zip(chunks, embeddings):
                await self.repo.save_doc_chunk(
                    document_id=document_id,
                    chunk_index=chunk.index,
                    chunk_text=chunk.text,
                    embedding=embedding,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                )

            await self.repo.update_document_processing_status(document_id, "completed")
            logger.info(f"[{document_id}] Document processing complete: {len(chunks)} chunks embedded")

        except Exception as e:
            logger.exception(f"[{document_id}] Document processing failed: {e}")
            await self.repo.update_document_processing_status(
                document_id, "failed", error_message=str(e)
            )
            raise

    @staticmethod
    async def _read_file(file_path: str) -> str:
        def _read() -> str:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        try:
            return await asyncio.to_thread(_read)
        except Exception as e:
            logger.warning(f"Could not read file {file_path}: {e}")
            return ""
