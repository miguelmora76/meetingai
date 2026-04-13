"""
Mock Slack client — logs all messages to stdout instead of sending to Slack.

Used when SLACK_ENABLED=false (the default). This lets the demo show Slack
notifications happening without requiring a real Slack workspace.
"""

import logging

from app.slack.base import SlackClient

logger = logging.getLogger("slack.mock")


class MockSlackClient(SlackClient):
    """Logs Slack messages to stdout instead of sending them."""

    def __init__(self, default_channel: str = "general"):
        self.channel = default_channel

    async def post_meeting_summary(self, meeting, summary: str) -> None:
        logger.info(
            f"[MOCK SLACK] #{self.channel} — 📝 Meeting Summary: {meeting.title}\n"
            f"  Preview: {summary[:200]}..."
        )

    async def post_action_items(self, meeting, items: list) -> None:
        logger.info(
            f"[MOCK SLACK] #{self.channel} — ✅ {len(items)} action items from {meeting.title}"
        )
        for item in items:
            assignee = item.get("assignee", "Unassigned") if isinstance(item, dict) else getattr(item, "assignee", "Unassigned")
            desc = item.get("description", "") if isinstance(item, dict) else getattr(item, "description", "")
            logger.info(f"  → @{assignee}: {desc}")

    async def post_message(self, channel: str, text: str, blocks: list[dict] | None = None) -> None:
        logger.info(f"[MOCK SLACK] #{channel}: {text[:200]}")

    async def notify_processing_complete(self, meeting) -> None:
        logger.info(
            f"[MOCK SLACK] #{self.channel} — ✅ Processing complete: {meeting.title}"
        )

    async def notify_incident_complete(self, incident, channel: str | None = None) -> None:
        target = channel or self.channel
        logger.info(
            f"[MOCK SLACK] #{target} — ✅ Incident analysis complete: {incident.title}"
        )

    async def open_modal(self, trigger_id: str, modal: dict) -> None:
        logger.info(
            f"[MOCK SLACK] open_modal trigger_id={trigger_id} "
            f"callback_id={modal.get('callback_id', '?')}"
        )
