"""
Slack client factory — returns the real or mock implementation based on config.
"""

import logging

from app.config.settings import Settings, get_settings
from app.slack.base import SlackClient
from app.slack.mock import MockSlackClient
from app.slack.real import RealSlackClient

logger = logging.getLogger(__name__)


def create_slack_client(settings: Settings | None = None) -> SlackClient:
    """
    Create the appropriate Slack client based on configuration.

    Returns RealSlackClient if SLACK_ENABLED=true and a bot token is present.
    Otherwise returns MockSlackClient that logs to stdout.
    """
    settings = settings or get_settings()

    if settings.slack_enabled and settings.slack_bot_token:
        logger.info("Slack integration ENABLED — using real client")
        return RealSlackClient(
            bot_token=settings.slack_bot_token,
            default_channel=settings.slack_default_channel,
        )
    else:
        logger.info("Slack integration DISABLED — using mock client (messages logged to stdout)")
        return MockSlackClient(
            default_channel=settings.slack_default_channel or "general",
        )
