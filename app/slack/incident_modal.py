"""
Slack Block Kit modal for logging incidents via the /incident slash command.
"""

from __future__ import annotations


def build_incident_modal(prefill_description: str = "") -> dict:
    """
    Return a full Slack modal payload for logging a new incident.

    The modal is submitted with callback_id='log_incident', which is handled
    by POST /slack/interactions.
    """
    return {
        "type": "modal",
        "callback_id": "log_incident",
        "title": {"type": "plain_text", "text": "Log Incident"},
        "submit": {"type": "plain_text", "text": "Log Incident"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "title_block",
                "label": {"type": "plain_text", "text": "Incident Title"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "title_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "e.g. Payment service latency spike",
                    },
                },
            },
            {
                "type": "input",
                "block_id": "severity_block",
                "label": {"type": "plain_text", "text": "Severity"},
                "element": {
                    "type": "static_select",
                    "action_id": "severity_select",
                    "initial_option": {
                        "text": {"type": "plain_text", "text": "SEV3 — Minor"},
                        "value": "SEV3",
                    },
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": "SEV1 — Critical"},
                            "value": "SEV1",
                        },
                        {
                            "text": {"type": "plain_text", "text": "SEV2 — Major"},
                            "value": "SEV2",
                        },
                        {
                            "text": {"type": "plain_text", "text": "SEV3 — Minor"},
                            "value": "SEV3",
                        },
                        {
                            "text": {"type": "plain_text", "text": "SEV4 — Low"},
                            "value": "SEV4",
                        },
                    ],
                },
            },
            {
                "type": "input",
                "block_id": "status_block",
                "label": {"type": "plain_text", "text": "Current Status"},
                "element": {
                    "type": "static_select",
                    "action_id": "status_select",
                    "initial_option": {
                        "text": {"type": "plain_text", "text": "Open"},
                        "value": "open",
                    },
                    "options": [
                        {"text": {"type": "plain_text", "text": "Open"}, "value": "open"},
                        {
                            "text": {"type": "plain_text", "text": "Mitigated"},
                            "value": "mitigated",
                        },
                        {
                            "text": {"type": "plain_text", "text": "Resolved"},
                            "value": "resolved",
                        },
                    ],
                },
            },
            {
                "type": "input",
                "block_id": "services_block",
                "label": {"type": "plain_text", "text": "Services Affected"},
                "optional": True,
                "element": {
                    "type": "plain_text_input",
                    "action_id": "services_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "e.g. payment-service, api-gateway",
                    },
                },
            },
            {
                "type": "input",
                "block_id": "description_block",
                "label": {"type": "plain_text", "text": "Description"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "description_input",
                    "multiline": True,
                    "initial_value": prefill_description,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Describe the incident — symptoms, impact, error messages, log snippets…",
                    },
                },
            },
        ],
    }
