"""
Airtable sync service — pushes processed data to an Airtable base.

Design decisions:
- pyairtable is synchronous; all network calls are wrapped in asyncio.to_thread
  so the event loop is never blocked.
- The service is a no-op when AIRTABLE_ENABLED=false, so it is always safe to
  call even in local dev environments that have no Airtable credentials.
- Field names in Airtable can be customised by renaming them in the base; this
  service uses the defaults documented in the runbook. The mapping is kept in
  one place (_build_*_fields) to make it easy to adjust.
- Multiple tables are supported: incidents, meetings, and documents each sync
  to their own table. A per-table cache avoids re-creating pyairtable handles.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from app.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

# ── Incident field name constants ─────────────────────────────────────────────
_INC_TITLE = "Title"
_INC_SEVERITY = "Severity"
_INC_STATUS = "Status"
_INC_SERVICES = "Services Affected"
_INC_EXEC_SUMMARY = "Executive Summary"
_INC_RCA = "Root Cause Analysis"
_INC_ACTION_ITEMS = "Action Items"
_INC_OCCURRED_AT = "Occurred At"
_INC_RESOLVED_AT = "Resolved At"
_INC_ENGINEERAI_ID = "EngineerAI ID"
_INC_ENGINEERAI_URL = "EngineerAI URL"

# ── Meeting field name constants ──────────────────────────────────────────────
_MTG_TITLE = "Title"
_MTG_DATE = "Date"
_MTG_PARTICIPANTS = "Participants"
_MTG_SUMMARY = "Summary"
_MTG_ACTION_ITEMS = "Action Items"
_MTG_DECISIONS = "Decisions"
_MTG_ENGINEERAI_ID = "EngineerAI ID"
_MTG_ENGINEERAI_URL = "EngineerAI URL"

# ── Document field name constants ─────────────────────────────────────────────
_DOC_TITLE = "Title"
_DOC_TYPE = "Doc Type"
_DOC_FILE_NAME = "File Name"
_DOC_STATUS = "Status"
_DOC_ENGINEERAI_ID = "EngineerAI ID"
_DOC_ENGINEERAI_URL = "EngineerAI URL"


class AirtableSyncService:
    """Pushes incident, meeting, and document data to Airtable after processing."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._tables: dict[str, Any] = {}  # table_name → pyairtable Table (lazy)

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

        fields = self._build_incident_fields(
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
                self._sync_push, self.settings.airtable_table_name, fields, existing_record_id
            )
            logger.info(f"[airtable] Incident {incident_id} synced → record {record_id}")
            return record_id
        except Exception as exc:
            logger.warning(f"[airtable] Failed to sync incident {incident_id}: {exc}")
            return None

    async def push_meeting(
        self,
        *,
        meeting_id: uuid.UUID,
        title: str,
        date: str | None,
        participants: list[str],
        summary: str | None,
        action_items: list[dict],
        decisions: list[dict],
        existing_record_id: str | None = None,
    ) -> str | None:
        """
        Create or update an Airtable record for the given meeting.

        Returns the Airtable record ID on success, or None if Airtable is
        disabled or if the push fails.
        """
        if not self.settings.airtable_enabled:
            return None

        fields = self._build_meeting_fields(
            meeting_id=meeting_id,
            title=title,
            date=date,
            participants=participants,
            summary=summary,
            action_items=action_items,
            decisions=decisions,
        )

        try:
            record_id = await asyncio.to_thread(
                self._sync_push,
                self.settings.airtable_meetings_table_name,
                fields,
                existing_record_id,
            )
            logger.info(f"[airtable] Meeting {meeting_id} synced → record {record_id}")
            return record_id
        except Exception as exc:
            logger.warning(f"[airtable] Failed to sync meeting {meeting_id}: {exc}")
            return None

    async def push_document(
        self,
        *,
        document_id: uuid.UUID,
        title: str,
        doc_type: str,
        file_name: str | None,
        processing_status: str,
        existing_record_id: str | None = None,
    ) -> str | None:
        """
        Create or update an Airtable record for the given document.

        Returns the Airtable record ID on success, or None if Airtable is
        disabled or if the push fails.
        """
        if not self.settings.airtable_enabled:
            return None

        fields = self._build_document_fields(
            document_id=document_id,
            title=title,
            doc_type=doc_type,
            file_name=file_name,
            processing_status=processing_status,
        )

        try:
            record_id = await asyncio.to_thread(
                self._sync_push,
                self.settings.airtable_docs_table_name,
                fields,
                existing_record_id,
            )
            logger.info(f"[airtable] Document {document_id} synced → record {record_id}")
            return record_id
        except Exception as exc:
            logger.warning(f"[airtable] Failed to sync document {document_id}: {exc}")
            return None

    async def update_incident_status(
        self,
        *,
        record_id: str,
        status: str,
        resolved_at: datetime | None = None,
    ) -> None:
        """
        Patch just the status (and optionally resolved_at) of an existing
        Airtable incident record. Safe to call even if Airtable is disabled.
        """
        if not self.settings.airtable_enabled:
            return

        fields: dict = {_INC_STATUS: status.capitalize()}
        if resolved_at:
            fields[_INC_RESOLVED_AT] = resolved_at.isoformat()

        try:
            await asyncio.to_thread(
                self._sync_update, self.settings.airtable_table_name, record_id, fields
            )
            logger.info(f"[airtable] Incident record {record_id} status updated → {status}")
        except Exception as exc:
            logger.warning(f"[airtable] Failed to update incident record {record_id}: {exc}")

    # ── Internal helpers ───────────────────────────────────────────────────

    def _get_table(self, table_name: str) -> Any:
        """Return a pyairtable Table for the given table name, caching per name."""
        if table_name not in self._tables:
            from pyairtable import Api  # import here so missing dep doesn't break startup

            api = Api(self.settings.airtable_api_key)
            self._tables[table_name] = api.table(
                self.settings.airtable_base_id,
                table_name,
            )
        return self._tables[table_name]

    def _sync_push(
        self, table_name: str, fields: dict, existing_record_id: str | None
    ) -> str:
        """Synchronous create/update — must be called inside asyncio.to_thread."""
        table = self._get_table(table_name)
        if existing_record_id:
            record = table.update(existing_record_id, fields)
        else:
            record = table.create(fields)
        return record["id"]

    def _sync_update(self, table_name: str, record_id: str, fields: dict) -> None:
        """Synchronous field-level update — must be called inside asyncio.to_thread."""
        table = self._get_table(table_name)
        table.update(record_id, fields)

    # ── Field builders ─────────────────────────────────────────────────────

    def _build_incident_fields(
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
        formatted_action_items = self._format_action_items(action_items)

        fields: dict = {
            _INC_TITLE: title,
            _INC_SEVERITY: severity.upper(),
            _INC_STATUS: status.capitalize(),
            _INC_SERVICES: ", ".join(services_affected) if services_affected else "",
            _INC_ENGINEERAI_ID: str(incident_id),
            _INC_ENGINEERAI_URL: f"{self.settings.app_base_url}/incidents/{incident_id}",
        }

        if executive_summary:
            fields[_INC_EXEC_SUMMARY] = executive_summary
        if root_cause_analysis:
            fields[_INC_RCA] = root_cause_analysis
        if formatted_action_items:
            fields[_INC_ACTION_ITEMS] = formatted_action_items
        if occurred_at:
            fields[_INC_OCCURRED_AT] = occurred_at.isoformat()

        return fields

    def _build_meeting_fields(
        self,
        *,
        meeting_id: uuid.UUID,
        title: str,
        date: str | None,
        participants: list[str],
        summary: str | None,
        action_items: list[dict],
        decisions: list[dict],
    ) -> dict:
        fields: dict = {
            _MTG_TITLE: title,
            _MTG_PARTICIPANTS: ", ".join(participants) if participants else "",
            _MTG_ENGINEERAI_ID: str(meeting_id),
            _MTG_ENGINEERAI_URL: f"{self.settings.app_base_url}/meetings/{meeting_id}",
        }

        if date:
            fields[_MTG_DATE] = date
        if summary:
            fields[_MTG_SUMMARY] = summary
        if action_items:
            fields[_MTG_ACTION_ITEMS] = self._format_action_items(action_items)
        if decisions:
            fields[_MTG_DECISIONS] = self._format_decisions(decisions)

        return fields

    def _build_document_fields(
        self,
        *,
        document_id: uuid.UUID,
        title: str,
        doc_type: str,
        file_name: str | None,
        processing_status: str,
    ) -> dict:
        fields: dict = {
            _DOC_TITLE: title,
            _DOC_TYPE: doc_type,
            _DOC_STATUS: processing_status.capitalize(),
            _DOC_ENGINEERAI_ID: str(document_id),
            _DOC_ENGINEERAI_URL: f"{self.settings.app_base_url}/knowledge-base/{document_id}",
        }

        if file_name:
            fields[_DOC_FILE_NAME] = file_name

        return fields

    # ── Formatting helpers ─────────────────────────────────────────────────

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

    @staticmethod
    def _format_decisions(decisions: list[dict]) -> str:
        """Render decisions as a plain-text numbered list."""
        if not decisions:
            return ""
        lines = []
        for i, dec in enumerate(decisions, 1):
            desc = dec.get("description", "")
            rationale = dec.get("rationale")
            line = f"{i}. {desc}"
            if rationale:
                line += f"\n   Rationale: {rationale}"
            lines.append(line)
        return "\n".join(lines)
