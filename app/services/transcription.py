"""
Transcription service — converts audio/video files to text.

Supports two modes:
  - "api": OpenAI Whisper API (fast, requires API key)
  - "local": Local whisper model via openai-whisper package (slow, free)
"""

import asyncio
import logging
from dataclasses import dataclass, field

from openai import AsyncOpenAI

from app.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str
    speaker: str | None = None


@dataclass
class TranscriptResult:
    full_text: str
    segments: list[TranscriptSegment] = field(default_factory=list)
    language: str = "en"
    duration_seconds: int = 0


class TranscriptionService:
    """Transcribes audio/video files to text using Whisper."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    async def transcribe(self, file_path: str) -> TranscriptResult:
        """
        Transcribe an audio/video file.

        Args:
            file_path: Path to the audio/video file on disk.

        Returns:
            TranscriptResult with full text, segments, and metadata.
        """
        logger.info(f"Transcribing: {file_path} (mode={self.settings.whisper_mode})")

        if self.settings.whisper_mode == "api":
            return await self._transcribe_api(file_path)
        else:
            return await self._transcribe_local(file_path)

    async def _transcribe_api(self, file_path: str) -> TranscriptResult:
        """Transcribe using the OpenAI Whisper API."""
        client = AsyncOpenAI(api_key=self.settings.openai_api_key)

        with open(file_path, "rb") as audio_file:
            # Use verbose_json format to get timestamps
            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )

        segments = []
        if hasattr(response, "segments") and response.segments:
            for seg in response.segments:
                segments.append(
                    TranscriptSegment(
                        start=seg.get("start", 0.0) if isinstance(seg, dict) else getattr(seg, "start", 0.0),
                        end=seg.get("end", 0.0) if isinstance(seg, dict) else getattr(seg, "end", 0.0),
                        text=(seg.get("text", "") if isinstance(seg, dict) else getattr(seg, "text", "")).strip(),
                    )
                )

        full_text = response.text if hasattr(response, "text") else " ".join(s.text for s in segments)
        duration = segments[-1].end if segments else 0

        logger.info(f"Transcription complete: {len(segments)} segments, {int(duration)}s duration")

        return TranscriptResult(
            full_text=full_text,
            segments=segments,
            language=getattr(response, "language", "en") or "en",
            duration_seconds=int(duration),
        )

    async def _transcribe_local(self, file_path: str) -> TranscriptResult:
        """
        Transcribe using faster-whisper (CTranslate2 backend, int8 quantization).

        Uses ~10x less memory than openai-whisper on CPU, making it viable
        for longer recordings without OOM kills.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run_local_transcription, file_path)

    def _run_local_transcription(self, file_path: str) -> TranscriptResult:
        """Synchronous transcription work — runs in a thread pool executor."""
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise RuntimeError(
                "Local whisper mode requires the faster-whisper package. "
                "Install it with: pip install faster-whisper"
            )

        logger.info(f"Loading faster-whisper model: {self.settings.whisper_model}")
        model = WhisperModel(
            self.settings.whisper_model,
            device="cpu",
            compute_type="int8",
        )

        logger.info("Running local transcription (this may take a while)...")
        segments_iter, info = model.transcribe(file_path, beam_size=5)

        segments = []
        full_text_parts = []
        for seg in segments_iter:
            segments.append(
                TranscriptSegment(
                    start=seg.start,
                    end=seg.end,
                    text=seg.text.strip(),
                )
            )
            full_text_parts.append(seg.text.strip())

        duration = segments[-1].end if segments else 0
        full_text = " ".join(full_text_parts)

        del model  # release CTranslate2 memory before embedding step

        logger.info(f"Transcription complete: {len(segments)} segments, {int(duration)}s duration")

        return TranscriptResult(
            full_text=full_text,
            segments=segments,
            language=info.language or "en",
            duration_seconds=int(duration),
        )
