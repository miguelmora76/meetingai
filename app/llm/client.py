"""
LLM client abstraction.

Uses the Anthropic SDK for chat completions (with tenacity retry) and a local
sentence-transformers model for embeddings (no external embedding API key required).

The AsyncAnthropic client is created once per LLMClient instance (not per call)
so the underlying httpx connection pool is reused across requests.
"""

import asyncio
import logging

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

# Retry on transient Anthropic API errors only (not on 4xx client errors).
_RETRYABLE = (
    anthropic.RateLimitError,
    anthropic.APITimeoutError,
    anthropic.InternalServerError,
)


class LLMClient:
    """Wraps the Anthropic API for completions and sentence-transformers for embeddings."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._embed_model = None  # lazy-loaded on first embed() call
        # Create the Anthropic client once — reuses the internal httpx connection pool.
        self._anthropic_client = anthropic.AsyncAnthropic(
            api_key=self.settings.anthropic_api_key,
            timeout=anthropic.Timeout(120.0, connect=10.0),
        )

    def _get_embed_model(self):
        if self._embed_model is None:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {self.settings.embedding_model}")
            self._embed_model = SentenceTransformer(self.settings.embedding_model)
        return self._embed_model

    async def complete(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: dict | None = None,
    ) -> str:
        """Send a chat completion request via the Anthropic API and return the text.

        Automatically retries on rate-limit, timeout, and server errors
        with exponential backoff (up to 3 attempts).
        """
        logger.info(f"LLM request: model={model}, system_len={len(system)}, user_len={len(user)}")

        @retry(
            retry=retry_if_exception_type(_RETRYABLE),
            wait=wait_exponential(multiplier=1, min=2, max=30),
            stop=stop_after_attempt(3),
            reraise=True,
        )
        async def _call() -> str:
            response = await self._anthropic_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                temperature=temperature,
            )
            content = response.content[0].text
            logger.info(
                f"LLM response: model={model}, "
                f"input_tokens={response.usage.input_tokens if response.usage else '?'}, "
                f"output_tokens={response.usage.output_tokens if response.usage else '?'}"
            )
            return content

        return await _call()

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using a local sentence-transformers model."""
        logger.info(f"Embedding request: {len(texts)} texts")

        loop = asyncio.get_event_loop()
        # Run both model loading (first call) and encoding in the executor so
        # the event loop is never blocked by the heavy SentenceTransformer init.
        embeddings = await loop.run_in_executor(
            None, lambda: self._get_embed_model().encode(texts).tolist()
        )
        return embeddings
