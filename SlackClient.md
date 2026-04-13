# Slack Integration

## Overview

The app is a **bidirectional Slack bot** — it both pushes notifications to Slack and handles inbound commands from engineers without leaving Slack.

There are three HTTP endpoints that handle all inbound Slack traffic, all under `/slack/`:

| Endpoint | Purpose |
|---|---|
| `POST /slack/events` | Slack Events API — URL verification + `app_mention` |
| `POST /slack/commands` | All slash commands |
| `POST /slack/interactions` | Modal submissions and button callbacks |

All three endpoints:
1. Verify the `X-Slack-Signature` HMAC (using `SLACK_SIGNING_SECRET`; skipped in dev if the secret is not set)
2. Return HTTP 200 immediately — Slack requires a response within 3 seconds
3. Hand off real work to `BackgroundTasks` so the actual LLM/DB operations run asynchronously

---

## Slash Commands

All five commands must point to `https://<host>/slack/commands` in the Slack app configuration.

| Command | Behavior |
|---|---|
| `/incident [text]` | Opens a Block Kit modal to log an incident; any text typed after the command pre-fills the description field |
| `/ask <question>` | RAG Q&A across all meetings, incidents, and docs — posts the answer back to the channel |
| `/search <query>` | Semantic search — posts top 5 results with excerpts |
| `/incidents` | Lists the 5 most recent incidents (severity, status, short ID) |
| `/meetings` | Lists the 5 most recent meetings (status, duration, short ID) |

`/ask` and `/search` send an ephemeral "Searching…" ack immediately, then post the real result asynchronously once the LLM/vector search completes.

---

## App Mention

When the bot is mentioned — `@EngineerAI what was decided in last week's Q3 planning meeting?` — the Events API fires an `app_mention` event to `POST /slack/events`. The bot strips the `<@UXXXXXXXX>` mention prefix, runs the same RAG pipeline as `/ask`, and replies **in-thread** to the original message.

---

## The `/incident` Modal Flow

```
User types: /incident payment service is down
      ↓
/slack/commands handler calls views.open with trigger_id
      ↓
Slack renders modal (title, severity, status, services, description)
Description is pre-filled with "payment service is down"
      ↓
User fills in fields and clicks "Log Incident"
      ↓
POST /slack/interactions  (callback_id = "log_incident")
      ↓
BackgroundTask: create incident in DB → ack user ("Incident Logged ⚡ analysis starting")
      ↓
Run IncidentProcessingService (Claude: postmortem + timeline + action items)
      ↓
Post full postmortem back to the originating channel
```

The originating channel is passed through `private_metadata` on the modal — the `/commands` handler sets `modal["private_metadata"] = channel_id` before calling `views.open`, and the interaction handler reads it back.

---

## Outbound (Proactive) Notifications

The app posts to Slack proactively when processing completes, without any user trigger:

- **Meeting processed** — `ProcessingService` calls `slack.notify_processing_complete()` after transcription + summarization finishes
- **Incident analyzed** — after `IncidentProcessingService` finishes, it posts a rich postmortem block (executive summary, root cause, top 3 action items with priority badges)

---

## Client Abstraction

```
SlackClientFactory (app/slack/factory.py)
  ├── SLACK_ENABLED=true  → RealSlackClient  (slack_sdk AsyncWebClient)
  └── SLACK_ENABLED=false → MockSlackClient  (logs to stdout, no HTTP calls)
```

`MockSlackClient` is the default — the three `/slack/*` endpoints are always registered and reachable, so you can develop and test the full flow without a real Slack workspace. Signature verification is also skipped when `SLACK_SIGNING_SECRET` is not set.

---

## Enabling the Real Bot

1. Create a Slack App at https://api.slack.com/apps → **From scratch**
2. **Slash Commands** — add `/incident`, `/ask`, `/search`, `/incidents`, `/meetings`, all with Request URL `https://<host>/slack/commands`
3. **Event Subscriptions** — enable, Request URL `https://<host>/slack/events`, subscribe to bot event: `app_mention`
4. **Interactivity & Shortcuts** — enable, Request URL `https://<host>/slack/interactions`
5. **OAuth & Permissions** — add Bot Token Scopes: `chat:write`, `chat:write.public`, `commands`, `im:write`, `views:open`
6. Install to workspace → copy **Bot User OAuth Token** → set as `SLACK_BOT_TOKEN`
7. Copy **Signing Secret** → set as `SLACK_SIGNING_SECRET`
8. In `k8s/configmap.yaml`: set `SLACK_ENABLED=true` and `SLACK_DEFAULT_CHANNEL`
9. In `k8s/secret.yaml`: set `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET`
10. Redeploy: `kubectl rollout restart deployment/meetingai-app -n meetingai`

For local development, expose the app with `ngrok http 8000` and use the ngrok URL as the Request URL in steps 2–4.

---

## Key Files

| File | Role |
|---|---|
| `app/api/slack_router.py` | The three endpoint handlers + signature verification dependency |
| `app/workers/slack_tasks.py` | Background tasks: `handle_slash_ask`, `handle_slash_search`, `handle_modal_log_incident`, `handle_list_incidents`, `handle_list_meetings` |
| `app/slack/message_builder.py` | Pure functions that build Block Kit payloads (no I/O) |
| `app/slack/incident_modal.py` | Block Kit modal definition for `/incident` |
| `app/slack/real.py` / `mock.py` | Real and mock client implementations |
| `app/slack/factory.py` | Picks real vs. mock based on `SLACK_ENABLED` |
