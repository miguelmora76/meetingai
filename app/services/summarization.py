"""
Summarization service — LLM-powered extraction of summaries, action items, and decisions.

Each extraction method is independent so they can run concurrently via asyncio.gather.
"""

import json
import logging
import re
from dataclasses import dataclass

from app.config.settings import Settings, get_settings
from app.llm.client import LLMClient
from app.llm.prompts import action_item_prompts, decision_prompts, meeting_summary_prompts

logger = logging.getLogger(__name__)


class SummarizationService:
    """Extracts structured information from meeting transcripts using LLMs."""

    def __init__(self, llm_client: LLMClient, settings: Settings | None = None):
        self.llm = llm_client
        self.settings = settings or get_settings()

    async def generate_summary(
        self, transcript: str, title: str = "", date: str = "", participants: str = ""
    ) -> str:
        """Generate a prose summary of the meeting."""
        system, user = meeting_summary_prompts(title, date, participants, transcript)
        summary = await self.llm.complete(
            model=self.settings.summarization_model,
            system=system,
            user=user,
        )
        logger.info(f"Generated summary: {len(summary)} chars")
        return summary

    async def extract_action_items(
        self, transcript: str, participants: str = ""
    ) -> list[dict]:
        """Extract action items as a list of dicts."""
        system, user = action_item_prompts(participants, transcript)
        response = await self.llm.complete(
            model=self.settings.extraction_model,
            system=system,
            user=user,
        )
        items = self._parse_json_list(response, "action items")
        logger.info(f"Extracted {len(items)} action items")
        return items

    async def extract_decisions(
        self, transcript: str, participants: str = ""
    ) -> list[dict]:
        """Extract decisions as a list of dicts."""
        system, user = decision_prompts(participants, transcript)
        response = await self.llm.complete(
            model=self.settings.extraction_model,
            system=system,
            user=user,
        )
        decisions = self._parse_json_list(response, "decisions")
        logger.info(f"Extracted {len(decisions)} decisions")
        return decisions

    def _parse_json_list(self, response: str, label: str) -> list[dict]:
        """
        Parse LLM response into a list of dicts.

        Handles:
        - Raw JSON arrays: [...]
        - Dict-wrapped arrays: {"action_items": [...]}
        - Markdown-fenced JSON: ```json\\n[...]\\n```
        - Falls back to regex extraction of a JSON array as last resort.
        Non-dict elements in the resulting list are silently filtered out.
        """
        if not response or not response.strip():
            return []

        try:
            # Strip markdown code fences if present
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            parsed = json.loads(text)

            if isinstance(parsed, list):
                result = [item for item in parsed if isinstance(item, dict)]
                if len(result) < len(parsed):
                    logger.warning(f"{label}: filtered out {len(parsed) - len(result)} non-dict items")
                return result

            if isinstance(parsed, dict):
                for value in parsed.values():
                    if isinstance(value, list):
                        result = [item for item in value if isinstance(item, dict)]
                        if len(result) < len(value):
                            logger.warning(f"{label}: filtered out {len(value) - len(result)} non-dict items")
                        return result

            logger.warning(f"Unexpected JSON shape for {label}: {type(parsed)}")
            return []

        except json.JSONDecodeError:
            # Last resort: try to extract a JSON array anywhere in the response
            match = re.search(r"\[.*\]", response, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group())
                    if isinstance(parsed, list):
                        result = [item for item in parsed if isinstance(item, dict)]
                        logger.warning(f"{label}: recovered {len(result)} items via regex fallback")
                        return result
                except json.JSONDecodeError:
                    pass
            logger.error(f"Failed to parse {label} JSON. Response: {response[:500]}")
            return []
