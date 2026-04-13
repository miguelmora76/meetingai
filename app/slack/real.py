"""
Real Slack client — sends messages via the Slack SDK.

Enabled only when SLACK_ENABLED=true and a valid bot token is provided.
"""

import logging

from slack_sdk.web.async_client import AsyncWebClient

from app.slack.base import SlackClient

logger = logging.getLogger("slack.real")


class RealSlackClient(SlackClient):
    """Sends real messages to Slack using the Slack SDK."""

    def __init__(self, bot_token: str, default_channel: str):
        self.client = AsyncWebClient(token=bot_token)
        self.channel = default_channel

    async def post_meeting_summary(self, meeting, summary: str) -> None:
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"📝 Meeting Summary: {meeting.title}"},
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": summary[:3000]},  # Slack block limit
            },
        ]
        await self.client.chat_postMessage(
            channel=self.channel,
            text=f"Meeting summary: {meeting.title}",
            blocks=blocks,
        )

    async def post_action_items(self, meeting, items: list) -> None:
        item_lines = []
        for item in items:
            assignee = item.get("assignee", "Unassigned") if isinstance(item, dict) else getattr(item, "assignee", "Unassigned")
            desc = item.get("description", "") if isinstance(item, dict) else getattr(item, "description", "")
            item_lines.append(f"• *@{assignee}*: {desc}")

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"✅ Action Items: {meeting.title}"},
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(item_lines)},
            },
        ]
        await self.client.chat_postMessage(
            channel=self.channel,
            text=f"{len(items)} action items from {meeting.title}",
            blocks=blocks,
        )

    async def post_message(self, channel: str, text: str, blocks: list[dict] | None = None) -> None:
        await self.client.chat_postMessage(
            channel=channel,
            text=text,
            blocks=blocks,
        )

    async def notify_processing_complete(self, meeting) -> None:
        await self.client.chat_postMessage(
            channel=self.channel,
            text=f"✅ Processing complete for *{meeting.title}*. View results in MeetingAI.",
        )

    async def notify_incident_complete(self, incident, channel: str | None = None) -> None:
        from app.slack.message_builder import incident_complete_message
        blocks = incident_complete_message(incident)
        await self.client.chat_postMessage(
            channel=channel or self.channel,
            text=f"Incident analysis complete: {incident.title}",
            blocks=blocks,
        )

    async def open_modal(self, trigger_id: str, modal: dict) -> None:
        await self.client.views_open(trigger_id=trigger_id, view=modal)
