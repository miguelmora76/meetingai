"""
Incident extraction service — parses LLM output for postmortems, timelines,
and remediation action items.
"""

import json
import logging
import re
from datetime import datetime

from app.config.settings import Settings, get_settings
from app.llm.client import LLMClient
from app.llm.prompts import (
    incident_action_items_prompts,
    incident_postmortem_prompts,
    incident_timeline_prompts,
)

logger = logging.getLogger(__name__)


class IncidentExtractionService:
    """Generates postmortem, timeline, and action items from incident text."""

    def __init__(self, llm_client: LLMClient, settings: Settings | None = None):
        self.llm = llm_client
        self.settings = settings or get_settings()

    async def generate_postmortem(
        self,
        incident_text: str,
        title: str,
        severity: str,
        services: list[str],
    ) -> tuple[str, str]:
        """
        Returns (executive_summary, root_cause_analysis).
        """
        services_str = ", ".join(services) if services else "unknown"
        system, user = incident_postmortem_prompts(title, severity, services_str, incident_text)
        raw = await self.llm.complete(
            model=self.settings.summarization_model,
            system=system,
            user=user,
        )

        exec_summary = ""
        rca = ""

        exec_match = re.search(
            r"EXECUTIVE_SUMMARY:\s*(.*?)(?=ROOT_CAUSE_ANALYSIS:|$)",
            raw,
            re.DOTALL | re.IGNORECASE,
        )
        rca_match = re.search(
            r"ROOT_CAUSE_ANALYSIS:\s*(.*)",
            raw,
            re.DOTALL | re.IGNORECASE,
        )

        if exec_match:
            exec_summary = exec_match.group(1).strip()
        if rca_match:
            rca = rca_match.group(1).strip()

        if not exec_summary and not rca:
            # Fallback: treat entire response as executive summary
            exec_summary = raw.strip()

        return exec_summary, rca

    async def extract_timeline(self, incident_text: str) -> list[dict]:
        """
        Returns list of timeline event dicts:
        [{occurred_at, description, event_type}]
        """
        system, user = incident_timeline_prompts(incident_text)
        raw = await self.llm.complete(
            model=self.settings.extraction_model,
            system=system,
            user=user,
        )

        try:
            events = self._parse_json(raw)
            if not isinstance(events, list):
                return []

            result = []
            for ev in events:
                occurred_at = None
                if ev.get("occurred_at"):
                    try:
                        occurred_at = datetime.fromisoformat(str(ev["occurred_at"]).replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass
                result.append(
                    {
                        "occurred_at": occurred_at,
                        "description": str(ev.get("description", "")),
                        "event_type": str(ev.get("event_type", "event")),
                    }
                )
            return result
        except Exception:
            logger.warning("Failed to parse timeline JSON; returning empty list")
            return []

    async def extract_action_items(self, incident_text: str, rca: str) -> list[dict]:
        """
        Returns list of action item dicts:
        [{description, assignee, priority, category}]
        """
        system, user = incident_action_items_prompts(incident_text, rca)
        raw = await self.llm.complete(
            model=self.settings.extraction_model,
            system=system,
            user=user,
        )

        try:
            items = self._parse_json(raw)
            if not isinstance(items, list):
                return []

            result = []
            for item in items:
                result.append(
                    {
                        "description": str(item.get("description", "")),
                        "assignee": item.get("assignee"),
                        "priority": str(item.get("priority", "medium")),
                        "category": item.get("category"),
                    }
                )
            return result
        except Exception:
            logger.warning("Failed to parse action items JSON; returning empty list")
            return []

    @staticmethod
    def _parse_json(text: str) -> object:
        """Extract JSON array or object from LLM response (handles markdown fences)."""
        # Strip markdown code fences
        text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
        return json.loads(text)
