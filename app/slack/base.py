"""
Slack client abstract base class.

All Slack interactions go through this interface so that real and mock
implementations are interchangeable.
"""

from abc import ABC, abstractmethod


class SlackClient(ABC):
    """Abstract interface for Slack interactions."""

    @abstractmethod
    async def post_meeting_summary(self, meeting, summary: str) -> None:
        """Post a formatted summary to the configured Slack channel."""

    @abstractmethod
    async def post_action_items(self, meeting, items: list) -> None:
        """Post action items with assignee mentions."""

    @abstractmethod
    async def post_message(self, channel: str, text: str, blocks: list[dict] | None = None) -> None:
        """Send a raw message to a channel."""

    @abstractmethod
    async def notify_processing_complete(self, meeting) -> None:
        """Notify that a meeting has finished processing."""

    @abstractmethod
    async def notify_incident_complete(self, incident, channel: str | None = None) -> None:
        """Notify that an incident's AI analysis has finished."""

    @abstractmethod
    async def open_modal(self, trigger_id: str, modal: dict) -> None:
        """Open a Slack modal in response to a slash command trigger."""
