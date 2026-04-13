"""
Slack Block Kit message formatting helpers.

All functions are pure (no I/O) and return Block Kit `blocks` arrays
ready to pass directly to chat_postMessage or chat_postEphemeral.
"""

from __future__ import annotations

import uuid
from typing import Any


def incident_created_message(
    incident_id: uuid.UUID,
    title: str,
    severity: str,
) -> list[dict[str, Any]]:
    """Ack message posted when an incident is first logged."""
    sev_emoji = {"SEV1": "🔴", "SEV2": "🟠", "SEV3": "🟡", "SEV4": "🟢"}.get(severity.upper(), "⚪")
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{sev_emoji} Incident Logged: {title}"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Severity:*\n{sev_emoji} {severity.upper()}"},
                {"type": "mrkdwn", "text": f"*ID:*\n`{str(incident_id)[:8]}…`"},
            ],
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "⚡ AI analysis starting — I'll post the postmortem here when it's ready."}
            ],
        },
    ]


def incident_complete_message(incident: Any) -> list[dict[str, Any]]:
    """Rich postmortem summary posted when incident analysis finishes."""
    sev_emoji = {"SEV1": "🔴", "SEV2": "🟠", "SEV3": "🟡", "SEV4": "🟢"}.get(
        (incident.severity or "").upper(), "⚪"
    )
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{sev_emoji} Incident Analysis Complete: {incident.title}",
            },
        },
        {"type": "divider"},
    ]

    # Postmortem executive summary
    if incident.postmortem:
        exec_summary = (incident.postmortem.executive_summary or "")[:2000]
        if exec_summary:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Executive Summary*\n{exec_summary}",
                    },
                }
            )

        rca = (incident.postmortem.root_cause_analysis or "")[:1500]
        if rca:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Root Cause*\n{rca}"},
                }
            )

    # Top 3 action items
    action_items = (incident.action_items or [])[:3]
    if action_items:
        blocks.append({"type": "divider"})
        lines = []
        for item in action_items:
            assignee = getattr(item, "assignee", None) or "Unassigned"
            desc = getattr(item, "description", "")
            priority = getattr(item, "priority", "")
            prio_badge = {"high": "🔺", "medium": "🔸", "low": "🔹"}.get(
                (priority or "").lower(), ""
            )
            lines.append(f"{prio_badge} *@{assignee}*: {desc}")
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Top Action Items*\n" + "\n".join(lines),
                },
            }
        )

    return blocks


def meeting_complete_message(meeting: Any) -> list[dict[str, Any]]:
    """Summary posted when meeting processing finishes."""
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📝 Meeting Processed: {meeting.title}"},
        },
        {"type": "divider"},
    ]

    if meeting.summary:
        summary_text = (meeting.summary.prose_summary or "")[:2000]
        if summary_text:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Summary*\n{summary_text}"},
                }
            )

    action_items = (meeting.action_items or [])[:5]
    if action_items:
        blocks.append({"type": "divider"})
        lines = []
        for item in action_items:
            assignee = getattr(item, "assignee", None) or "Unassigned"
            desc = getattr(item, "description", "")
            lines.append(f"• *@{assignee}*: {desc}")
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Action Items*\n" + "\n".join(lines),
                },
            }
        )

    return blocks


def qa_answer_message(
    question: str,
    answer: str,
    sources: list[Any],
) -> list[dict[str, Any]]:
    """RAG answer with collapsible sources."""
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "EngineerAI Answer"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Q:* {question[:300]}"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": answer[:3000]},
        },
    ]

    # Top 3 sources
    top_sources = sources[:3]
    if top_sources:
        source_lines = []
        type_icons = {"meeting": "📹", "incident": "🚨", "doc": "📄", "document": "📄"}
        for src in top_sources:
            src_type = getattr(src, "source_type", None) or "meeting"
            src_title = getattr(src, "source_title", None) or getattr(src, "meeting_title", "Unknown")
            icon = type_icons.get(src_type, "📎")
            score = getattr(src, "similarity_score", None)
            score_str = f" ({score:.0%})" if score is not None else ""
            source_lines.append(f"{icon} {src_title}{score_str}")
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "*Sources:* " + "  ·  ".join(source_lines),
                    }
                ],
            }
        )

    return blocks


def search_results_message(
    query: str,
    results: list[Any],
) -> list[dict[str, Any]]:
    """Search results with type badges and excerpts."""
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Search: {query[:80]}"},
        },
    ]

    if not results:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "_No results found._"},
            }
        )
        return blocks

    type_icons = {"meeting": "📹", "incident": "🚨", "doc": "📄", "document": "📄"}
    for result in results[:5]:
        src_type = getattr(result, "source_type", None) or "meeting"
        src_title = getattr(result, "source_title", None) or getattr(result, "meeting_title", "Unknown")
        icon = type_icons.get(src_type, "📎")
        score = getattr(result, "similarity_score", None)
        excerpt = (getattr(result, "chunk_text", "") or "")[:200]
        score_bar = _similarity_bar(score) if score is not None else ""

        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"{icon} *{src_title}*  `{src_type}`  {score_bar}\n"
                        f"_{excerpt}…_"
                    ),
                },
            }
        )

    return blocks


def incident_list_message(incidents: list[Any]) -> list[dict[str, Any]]:
    """Compact list of recent incidents."""
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Recent Incidents"},
        },
    ]

    if not incidents:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "_No incidents found._"},
            }
        )
        return blocks

    sev_emojis = {"SEV1": "🔴", "SEV2": "🟠", "SEV3": "🟡", "SEV4": "🟢"}
    status_emojis = {"open": "🔓", "mitigated": "🔧", "resolved": "✅"}

    for incident in incidents:
        sev = (getattr(incident, "severity", None) or "").upper()
        status = (getattr(incident, "status", None) or "open").lower()
        sev_icon = sev_emojis.get(sev, "⚪")
        status_icon = status_emojis.get(status, "❓")
        title = getattr(incident, "title", "Untitled")
        proc_status = getattr(incident, "processing_status", "")
        short_id = str(getattr(incident, "id", "")).split("-")[0]

        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{sev_icon} *{title}* {status_icon} `{proc_status}`  `#{short_id}`",
                },
            }
        )

    return blocks


def meeting_list_message(meetings: list[Any]) -> list[dict[str, Any]]:
    """Compact list of recent meetings."""
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Recent Meetings"},
        },
    ]

    if not meetings:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "_No meetings found._"},
            }
        )
        return blocks

    status_emojis = {"pending": "⏳", "processing": "⚙️", "completed": "✅", "failed": "❌"}

    for meeting in meetings:
        title = getattr(meeting, "title", "Untitled")
        status = (getattr(meeting, "status", "") or "").lower()
        icon = status_emojis.get(status, "📹")
        duration = getattr(meeting, "duration_seconds", None)
        dur_str = f" · {duration // 60}m" if duration else ""
        short_id = str(getattr(meeting, "id", "")).split("-")[0]

        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{icon} *{title}*{dur_str}  `{status}`  `#{short_id}`",
                },
            }
        )

    return blocks


def error_message(text: str) -> list[dict[str, Any]]:
    """Generic error block."""
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"⚠️ {text}"},
        }
    ]


# ── helpers ───────────────────────────────────────────────────────────────

def _similarity_bar(score: float, width: int = 5) -> str:
    """Convert a similarity score (0–1) to a small text bar."""
    filled = round(score * width)
    return "█" * filled + "░" * (width - filled)
