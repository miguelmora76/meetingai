"""
Slack bot route handlers.

Three endpoints handle all inbound Slack traffic:
  POST /slack/events       — Slack Events API (URL verification + app_mention)
  POST /slack/commands     — All slash commands
  POST /slack/interactions — Modal submissions and button callbacks

Every handler:
  1. Verifies the X-Slack-Signature HMAC (dependency)
  2. Returns HTTP 200 immediately (Slack 3-second window)
  3. Dispatches work to BackgroundTasks

This router is only wired up when SLACK_ENABLED=true.
"""

from __future__ import annotations

import json
import logging
import urllib.parse

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, Response
from slack_sdk.signature import SignatureVerifier

from app.config.settings import Settings, get_settings
from app.slack.factory import create_slack_client
from app.slack.incident_modal import build_incident_modal
from app.workers.slack_tasks import (
    handle_list_incidents,
    handle_list_meetings,
    handle_modal_log_incident,
    handle_slash_ask,
    handle_slash_search,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/slack", tags=["slack"])


# ── Signature verification dependency ─────────────────────────────────────


async def verify_slack_signature(
    request: Request,
    x_slack_signature: str = Header(..., alias="x-slack-signature"),
    x_slack_request_timestamp: str = Header(..., alias="x-slack-request-timestamp"),
    settings: Settings = Depends(get_settings),
) -> None:
    """Reject requests that don't carry a valid Slack HMAC signature."""
    if not settings.slack_signing_secret:
        # No secret configured — skip verification (dev mode)
        return

    body = await request.body()
    verifier = SignatureVerifier(settings.slack_signing_secret)
    if not verifier.is_valid(body, x_slack_request_timestamp, x_slack_signature):
        raise HTTPException(status_code=403, detail="Invalid Slack signature")


# ── /slack/events ──────────────────────────────────────────────────────────


@router.post("/events", dependencies=[Depends(verify_slack_signature)])
async def slack_events(
    request: Request,
    background_tasks: BackgroundTasks,
) -> Response:
    """
    Handle Slack Events API payloads.

    Supported events:
      - url_verification challenge (one-time setup)
      - app_mention → RAG Q&A answer posted in-thread
    """
    body = await request.json()

    # URL verification handshake (Slack sends this once when you set up the endpoint)
    if body.get("type") == "url_verification":
        return Response(
            content=json.dumps({"challenge": body["challenge"]}),
            media_type="application/json",
        )

    event = body.get("event", {})
    event_type = event.get("type")

    if event_type == "app_mention":
        # Strip the bot mention (<@UXXXXXXXX>) from the text
        text: str = event.get("text", "")
        import re
        question = re.sub(r"<@[A-Z0-9]+>", "", text).strip()
        channel = event.get("channel", "")
        thread_ts = event.get("thread_ts") or event.get("ts")

        if question:
            background_tasks.add_task(
                handle_slash_ask,
                question=question,
                channel=channel,
                user_id=event.get("user", ""),
                thread_ts=thread_ts,
            )

    return Response(status_code=200)


# ── /slack/commands ────────────────────────────────────────────────────────


@router.post("/commands", dependencies=[Depends(verify_slack_signature)])
async def slack_commands(
    request: Request,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
) -> Response:
    """
    Dispatch all slash commands.

    Supported commands:
      /incident [text]  — Open log-incident modal (text pre-fills description)
      /ask <question>   — RAG Q&A
      /search <query>   — Semantic search
      /incidents        — List 5 most recent incidents
      /meetings         — List 5 most recent meetings
    """
    body_bytes = await request.body()
    params = dict(urllib.parse.parse_qsl(body_bytes.decode()))

    command: str = params.get("command", "")
    text: str = params.get("text", "").strip()
    channel: str = params.get("channel_id", "")
    user_id: str = params.get("user_id", "")
    trigger_id: str = params.get("trigger_id", "")

    logger.info(f"Slash command: {command!r} text={text!r} channel={channel}")

    if command == "/incident":
        # Open the incident modal; prefill description with any text typed after the command.
        # Store the originating channel in private_metadata so the interaction handler can
        # post the incident notification to the right channel.
        slack = create_slack_client()
        modal = build_incident_modal(prefill_description=text)
        modal["private_metadata"] = channel
        try:
            await slack.open_modal(trigger_id=trigger_id, modal=modal)
        except Exception:
            logger.exception("Failed to open incident modal")
        return Response(status_code=200)

    if command == "/ask":
        if not text:
            return Response(
                content=json.dumps({
                    "response_type": "ephemeral",
                    "text": "Usage: `/ask <your question>`",
                }),
                media_type="application/json",
            )
        background_tasks.add_task(
            handle_slash_ask,
            question=text,
            channel=channel,
            user_id=user_id,
        )
        return Response(
            content=json.dumps({
                "response_type": "ephemeral",
                "text": f"Searching for an answer to: _{text}_…",
            }),
            media_type="application/json",
        )

    if command == "/search":
        if not text:
            return Response(
                content=json.dumps({
                    "response_type": "ephemeral",
                    "text": "Usage: `/search <query>`",
                }),
                media_type="application/json",
            )
        background_tasks.add_task(
            handle_slash_search,
            query=text,
            channel=channel,
            user_id=user_id,
        )
        return Response(
            content=json.dumps({
                "response_type": "ephemeral",
                "text": f"Searching for: _{text}_…",
            }),
            media_type="application/json",
        )

    if command == "/incidents":
        background_tasks.add_task(handle_list_incidents, channel=channel)
        return Response(status_code=200)

    if command == "/meetings":
        background_tasks.add_task(handle_list_meetings, channel=channel)
        return Response(status_code=200)

    # Unknown command
    logger.warning(f"Unknown slash command: {command!r}")
    return Response(status_code=200)


# ── /slack/interactions ────────────────────────────────────────────────────


@router.post("/interactions", dependencies=[Depends(verify_slack_signature)])
async def slack_interactions(
    request: Request,
    background_tasks: BackgroundTasks,
) -> Response:
    """
    Handle modal submissions and interactive component callbacks.

    Supported callback IDs:
      log_incident — submitted from the /incident modal
    """
    body_bytes = await request.body()
    params = dict(urllib.parse.parse_qsl(body_bytes.decode()))
    payload_raw = params.get("payload", "{}")

    try:
        payload = json.loads(payload_raw)
    except json.JSONDecodeError:
        logger.warning("Could not parse Slack interaction payload")
        return Response(status_code=200)

    interaction_type = payload.get("type")
    callback_id = payload.get("view", {}).get("callback_id") or payload.get("callback_id", "")

    logger.info(f"Slack interaction: type={interaction_type!r} callback={callback_id!r}")

    if interaction_type == "view_submission" and callback_id == "log_incident":
        values = payload.get("view", {}).get("state", {}).get("values", {})
        channel = _extract_channel_from_metadata(payload)
        user_id = payload.get("user", {}).get("id", "")

        title = _block_value(values, "title_block", "title_input")
        severity = _block_value(values, "severity_block", "severity_select", select=True)
        status = _block_value(values, "status_block", "status_select", select=True)
        services_raw = _block_value(values, "services_block", "services_input") or ""
        description = _block_value(values, "description_block", "description_input") or ""
        services = [s.strip() for s in services_raw.split(",") if s.strip()]

        background_tasks.add_task(
            handle_modal_log_incident,
            title=title or "Untitled Incident",
            severity=severity or "SEV3",
            status=status or "open",
            services_affected=services,
            description=description,
            channel=channel,
            user_id=user_id,
        )

        # Return empty 200 to close the modal
        return Response(status_code=200)

    return Response(status_code=200)


# ── helpers ────────────────────────────────────────────────────────────────


def _block_value(
    values: dict,
    block_id: str,
    action_id: str,
    select: bool = False,
) -> str | None:
    """Extract a value from Slack modal state values."""
    block = values.get(block_id, {})
    action = block.get(action_id, {})
    if select:
        selected = action.get("selected_option") or {}
        return selected.get("value")
    return action.get("value")


def _extract_channel_from_metadata(payload: dict) -> str:
    """
    The modal payload doesn't natively carry the originating channel.
    We store it in private_metadata as plain text when opening the modal.
    If absent, fall back to the user's DM channel (user_id as channel).
    """
    meta = payload.get("view", {}).get("private_metadata", "")
    if meta:
        return meta
    # Fall back to DM with the user
    return payload.get("user", {}).get("id", "")
