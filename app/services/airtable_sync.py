"""
Airtable sync service — pushes processed incident data to an Airtable base.

Design decisions:
- pyairtable is synchronous; all network calls are wrapped in asyncio.to_thread
  so the event loop is never blocked.
- The service is a no-op when AIRTABLE_ENABLED=false, so it is always safe to
  call even in local dev environments that have no Airtable credentials.
- Field names in Airtable can be customised by renaming them in the base; this
  service uses the defaults documented in the runbook. The mapping is kept in
  one place (_build_fields) to make it easy to adjust.
"""

import asyncio
import logging
import uuid
from datetime import datetime

from app.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

# Airtable field name constants — rename here if your base uses different names.
_FIELD_TITLE = "Title"
_FIELD_SEVERITY = "Severity"
_FIELD_STATUS = "Status"
_FIELD_SERVICES = "Services Affected"
_FIELD_EXEC_SUMMARY = "Executive Summary"
_FIELD_RCA = "Root Cause Analysis"
_FIELD_ACTION_ITEMS = "Action Items"
_FIELD_OCCURRED_AT = "Occurred At"
_FIELD_ENGINEERAI_ID = "EngineerAI ID"
_FIELD_ENGINEERAI_URL = "EngineerAI URL"


class AirtableSyncService:
    """Pushes incident data to Airtable after processing completes."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._table = None  # lazy-initialised on first use

    # ── Public API ─────────────────────────────────────────────────────────

    async def push_incident(
        self,
        *,
        incident_id: uuid.UUID,
        title: str,
        severity: str,
        status: str,
        services_affected: list[str],
        executive_summary: str | None,
        root_cause_analysis: str | None,
        action_items: list[dict],
        occurred_at: datetime | None,
        existing_record_id: str | None = None,
    ) -> str | None:
        """
        Create or update an Airtable record for the given incident.

        Returns the Airtable record ID on success, or None if Airtable is
        disabled or if the push fails (failure is logged but not re-raised so
        it never breaks the main processing pipeline).
        """
        if not self.settings.airtable_enabled:
            return None

        fields = self._build_fields(
            incident_id=incident_id,
            title=title,
            severity=severity,
            status=status,
            services_affected=services_affected,
            executive_summary=executive_summary,
            root_cause_analysis=root_cause_analysis,
            action_items=action_items,
            occurred_at=occurred_at,
        )

        try:
            record_id = await asyncio.to_thread(
                self._sync_push, fields, existing_record_id
            )
            logger.info(f"[airtable] Incident {incident_id} synced → record {record_id}")
            return record_id
        except Exception as exc:
            logger.warning(f"[airtable] Failed to sync incident {incident_id}: {exc}")
            return None

    # ── Internal helpers ───────────────────────────────────────────────────

    def _get_table(self):
        """Return a pyairtable Table, initialising the client on first call."""
        if self._table is None:
            from pyairtable import Api  # import here so missing dep doesn't break startup

            api = Api(self.settings.airtable_api_key)
            self._table = api.table(
                self.settings.airtable_base_id,
                self.settings.airtable_table_name,
            )
        return self._table

    def _sync_push(self, fields: dict, existing_record_id: str | None) -> str:
        """Synchronous create/update — must be called inside asyncio.to_thread."""
        table = self._get_table()
        if existing_record_id:
            record = table.update(existing_record_id, fields)
        else:
            record = table.create(fields)
        return record["id"]

    def _build_fields(
        self,
        *,
        incident_id: uuid.UUID,
        title: str,
        severity: str,
        status: str,
        services_affected: list[str],
        executive_summary: str | None,
        root_cause_analysis: str | None,
        action_items: list[dict],
        occurred_at: datetime | None,
    ) -> dict:
        """Map incident data to Airtable field names."""
        formatted_action_items = self._format_action_items(action_items)

        fields: dict = {
            _FIELD_TITLE: title,
            _FIELD_SEVERITY: severity.upper(),
            _FIELD_STATUS: status.capitalize(),
            _FIELD_SERVICES: ", ".join(services_affected) if services_affected else "",
            _FIELD_ENGINEERAI_ID: str(incident_id),
            _FIELD_ENGINEERAI_URL: f"{self.settings.app_base_url}/incidents/{incident_id}",
        }

        if executive_summary:
            fields[_FIELD_EXEC_SUMMARY] = executive_summary
        if root_cause_analysis:
            fields[_FIELD_RCA] = root_cause_analysis
        if formatted_action_items:
            fields[_FIELD_ACTION_ITEMS] = formatted_action_items
        if occurred_at:
            # Airtable date fields expect ISO-8601 strings
            fields[_FIELD_OCCURRED_AT] = occurred_at.isoformat()

        return fields

    @staticmethod
    def _format_action_items(items: list[dict]) -> str:
        """Render action items as a plain-text numbered list."""
        if not items:
            return ""
        lines = []
        for i, item in enumerate(items, 1):
            desc = item.get("description", "")
            assignee = item.get("assignee")
            priority = item.get("priority", "medium")
            line = f"{i}. [{priority.upper()}] {desc}"
            if assignee:
                line += f" → {assignee}"
            lines.append(line)
        return "\n".join(lines)
