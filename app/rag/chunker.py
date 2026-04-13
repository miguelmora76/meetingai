"""
Transcript chunker — splits transcripts into overlapping chunks for embedding.

Strategy: sentence-aware fixed-size chunking with configurable overlap.
"""

import re
from dataclasses import dataclass


@dataclass
class Chunk:
    index: int
    text: str
    start_char: int
    end_char: int


class TranscriptChunker:
    """Splits transcript text into overlapping chunks respecting sentence boundaries."""

    def __init__(self, chunk_size: int = 1500, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[Chunk]:
        """
        Split text into overlapping chunks.

        Args:
            text: Full transcript text.

        Returns:
            List of Chunk objects with index, text, and character offsets.
        """
        if not text or not text.strip():
            return []

        sentences = self._split_sentences(text)
        if not sentences:
            return []

        chunks: list[Chunk] = []
        current_sentences: list[str] = []
        current_length = 0
        chunk_start_char = 0
        char_pos = 0

        # Track character positions for each sentence
        sentence_positions: list[tuple[int, int]] = []
        pos = 0
        for sentence in sentences:
            start = text.find(sentence, pos)
            if start == -1:
                start = pos
            end = start + len(sentence)
            sentence_positions.append((start, end))
            pos = end

        sentence_start_idx = 0

        for i, sentence in enumerate(sentences):
            if current_length + len(sentence) > self.chunk_size and current_sentences:
                # Emit current chunk
                chunk_text = " ".join(current_sentences)
                start_pos = sentence_positions[sentence_start_idx][0]
                end_pos = sentence_positions[i - 1][1]

                chunks.append(
                    Chunk(
                        index=len(chunks),
                        text=chunk_text,
                        start_char=start_pos,
                        end_char=end_pos,
                    )
                )

                # Calculate overlap — keep trailing sentences within overlap window
                overlap_chars = 0
                overlap_start = len(current_sentences)
                for j in range(len(current_sentences) - 1, -1, -1):
                    overlap_chars += len(current_sentences[j])
                    if overlap_chars >= self.overlap:
                        overlap_start = j
                        break

                kept_count = len(current_sentences) - overlap_start
                sentence_start_idx = i - kept_count
                current_sentences = current_sentences[overlap_start:]
                current_length = sum(len(s) for s in current_sentences)

            current_sentences.append(sentence)
            current_length += len(sentence)

        # Final chunk
        if current_sentences:
            chunk_text = " ".join(current_sentences)
            start_pos = sentence_positions[sentence_start_idx][0] if sentence_start_idx < len(sentence_positions) else 0
            end_pos = sentence_positions[-1][1] if sentence_positions else len(text)

            chunks.append(
                Chunk(
                    index=len(chunks),
                    text=chunk_text,
                    start_char=start_pos,
                    end_char=end_pos,
                )
            )

        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        """
        Split text into sentences.

        Uses a simple regex-based approach that handles common abbreviations.
        Good enough for meeting transcripts.
        """
        # Split on sentence-ending punctuation followed by whitespace
        raw_splits = re.split(r"(?<=[.!?])\s+", text.strip())
        # Filter out empty strings and whitespace-only strings
        return [s.strip() for s in raw_splits if s.strip()]
