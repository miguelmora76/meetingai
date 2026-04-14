# Airtable Integration

EngineerAI syncs processed meetings, incidents, and knowledge-base documents to Airtable. The integration is one-directional by default (app → Airtable) and optionally bidirectional via Airtable automations posting back to a webhook endpoint.

---

## Configuration

Set the following environment variables (copy `.env.example` → `.env`):

| Variable | Required | Default | Description |
|---|---|---|---|
| `AIRTABLE_ENABLED` | Yes | `false` | Set to `true` to activate sync |
| `AIRTABLE_API_KEY` | Yes | — | Personal access token from Airtable |
| `AIRTABLE_BASE_ID` | Yes | — | Base ID (starts with `app…`) |
| `AIRTABLE_TABLE_NAME` | No | `Incidents` | Table name for incidents |
| `AIRTABLE_MEETINGS_TABLE_NAME` | No | `Meetings` | Table name for meetings |
| `AIRTABLE_DOCS_TABLE_NAME` | No | `Documents` | Table name for knowledge-base docs |
| `AIRTABLE_WEBHOOK_SECRET` | No | — | Bearer token for the bidirectional webhook (leave empty to disable) |
| `APP_BASE_URL` | No | `http://localhost:8000` | Base URL written into `EngineerAI URL` fields |

---

## Airtable Table Setup

Create three tables in your Airtable base with the following fields. Field names must match exactly (or update the constants in `app/services/airtable_sync.py`).

### Incidents table (`AIRTABLE_TABLE_NAME`)

| Field | Type |
|---|---|
| Title | Single line text |
| Severity | Single line text |
| Status | Single line text |
| Services Affected | Single line text |
| Executive Summary | Long text |
| Root Cause Analysis | Long text |
| Action Items | Long text |
| Occurred At | Date |
| Resolved At | Date |
| EngineerAI ID | Single line text |
| EngineerAI URL | URL |

### Meetings table (`AIRTABLE_MEETINGS_TABLE_NAME`)

| Field | Type |
|---|---|
| Title | Single line text |
| Date | Single line text |
| Participants | Single line text |
| Summary | Long text |
| Action Items | Long text |
| Decisions | Long text |
| EngineerAI ID | Single line text |
| EngineerAI URL | URL |

### Documents table (`AIRTABLE_DOCS_TABLE_NAME`)

| Field | Type |
|---|---|
| Title | Single line text |
| Doc Type | Single line text |
| File Name | Single line text |
| Status | Single line text |
| EngineerAI ID | Single line text |
| EngineerAI URL | URL |

---

## How Sync Works

### Automatic sync (app → Airtable)

Sync fires automatically as part of each processing pipeline, after all AI analysis completes:

| Resource | Trigger | What is synced |
|---|---|---|
| Incident | After `IncidentProcessingService` completes | Title, severity, status, services, exec summary, RCA, action items, occurred at |
| Meeting | After `ProcessingService` completes | Title, date, participants, summary, action items, decisions |
| Document | After `DocProcessingService` completes | Title, doc type, file name, status |

Sync is **non-blocking**: a failure logs a warning but never causes the processing pipeline to fail or the incident/meeting to be marked as errored.

The Airtable record ID is stored back in the database (`airtable_record_id` column on `incidents`, `meetings`, and `documents`). Subsequent syncs use it to update the existing record rather than creating a duplicate.

### Incident status auto-update

When an incident's status changes via `PATCH /incidents/{id}`, the app immediately patches the `Status` (and optionally `Resolved At`) field on the existing Airtable record.

### Manual re-sync

Useful when an Airtable record was deleted, fields need refreshing, or the initial sync failed:

```
POST /incidents/{id}/sync
POST /meetings/{id}/sync
POST /knowledge-base/{id}/sync
```

All return:

```json
{
  "airtable_record_id": "recXXXXXXXXXXXXXX",
  "synced": true
}
```

Returns `503` if `AIRTABLE_ENABLED=false`.

---

## Bidirectional Sync (Airtable → App)

Status changes made directly in Airtable can be pushed back to the app via an Airtable automation.

### Webhook endpoint

```
POST /airtable/webhook
Authorization: Bearer {AIRTABLE_WEBHOOK_SECRET}
Content-Type: application/json
```

**Request body:**

```json
{
  "resource_type": "incident",
  "engineerai_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "resolved",
  "resolved_at": "2026-04-14T15:30:00Z"
}
```

| Field | Values |
|---|---|
| `resource_type` | `incident` or `meeting` |
| `engineerai_id` | UUID from the `EngineerAI ID` field in Airtable |
| `status` | Incident: `open`, `mitigated`, `resolved`, `closed` · Meeting: `uploaded`, `processing`, `completed`, `failed` |
| `resolved_at` | ISO-8601 datetime, optional |

**Response:** `{"ok": true}`

Returns `401` for a wrong secret, `403` if `AIRTABLE_WEBHOOK_SECRET` is not configured, `400` for invalid payload, `404` if the record ID is not found.

### Setting up the Airtable automation

1. In your Airtable base, open **Automations** → **+ New automation**
2. Trigger: **When a field changes** → select the `Status` field in the Incidents table
3. Action: **Send an HTTP request**
   - Method: `POST`
   - URL: `{APP_BASE_URL}/airtable/webhook`
   - Headers: `Authorization: Bearer {AIRTABLE_WEBHOOK_SECRET}`
   - Body (JSON):
     ```json
     {
       "resource_type": "incident",
       "engineerai_id": "{{EngineerAI ID}}",
       "status": "{{Status}}"
     }
     ```
4. Repeat for the Meetings table with `"resource_type": "meeting"`.

---

## Frontend

When a resource has been synced, a **"Synced to Airtable"** badge appears:

- Incident detail page — in the metadata row alongside severity and status
- Meeting detail page — in the date/duration row

The badge is shown whenever the `airtable_record_id` field is non-null on the returned resource.

---

## Implementation Reference

| Purpose | File |
|---|---|
| Sync service (all push/update logic) | `app/services/airtable_sync.py` |
| Field name constants | `app/services/airtable_sync.py` (top of file) |
| Webhook endpoint | `app/api/airtable_router.py` |
| Incident PATCH + sync endpoints | `app/api/incidents.py` |
| Meeting sync endpoint | `app/api/meetings.py` |
| Document sync endpoint | `app/api/docs.py` |
| DB migration (columns) | `migrations/versions/005_airtable_meetings_docs.py` |
| ORM models | `app/models/database.py` (`Meeting`, `Document`) |
| Pydantic schemas | `app/models/schemas.py` (`AirtableSyncResponse`, `IncidentStatusUpdateRequest`) |
| Settings | `app/config/settings.py` |
| Frontend types | `frontend/src/types/api.ts` |
| Frontend badge — incidents | `frontend/src/components/incidents/IncidentDetail.tsx` |
| Frontend badge — meetings | `frontend/src/components/meetings/MeetingDetail.tsx` |

---

## Running the Migration

```bash
# Against a running database (Docker Compose or Kubernetes)
alembic upgrade head

# Or via the Kubernetes init container (runs automatically on deploy)
kubectl rollout restart deployment/meetingai-app -n meetingai
```