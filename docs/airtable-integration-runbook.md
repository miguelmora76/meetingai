# Airtable Integration Runbook

This runbook covers how to set up, configure, verify, and troubleshoot the
Airtable incident-sync feature. When enabled, every incident that finishes
processing in EngineerAI is automatically pushed to a designated Airtable
table. If an incident is processed more than once (re-triggered), the existing
Airtable record is updated in place rather than duplicated.

---

## Table of Contents

1. [How It Works](#1-how-it-works)
2. [Prerequisites](#2-prerequisites)
3. [Airtable Setup](#3-airtable-setup)
4. [Application Configuration](#4-application-configuration)
5. [Database Migration](#5-database-migration)
6. [Deploying the Change](#6-deploying-the-change)
7. [Verifying the Integration](#7-verifying-the-integration)
8. [Field Reference](#8-field-reference)
9. [Customising Field Names](#9-customising-field-names)
10. [Troubleshooting](#10-troubleshooting)
11. [Disabling the Integration](#11-disabling-the-integration)

---

## 1. How It Works

```
POST /incidents  →  IncidentProcessingService
                        ├─ extract postmortem + timeline + action items (Claude)
                        ├─ embed for RAG (pgvector)
                        └─ AirtableSyncService.push_incident()
                               ├─ if no airtable_record_id → table.create()
                               └─ if airtable_record_id exists → table.update()
                         → store returned record ID on incidents.airtable_record_id
```

Key design choices:

- **Non-blocking**: Airtable push runs after processing completes. A failure
  logs a warning but does **not** fail the incident or set `processing_status`
  to `"failed"`.
- **Idempotent**: The `airtable_record_id` column ensures re-processing an
  incident updates the same row rather than creating a duplicate.
- **Opt-in**: The sync is completely inert when `AIRTABLE_ENABLED=false`
  (the default), so no credentials are needed in local dev.

---

## 2. Prerequisites

| Requirement | Notes |
|-------------|-------|
| Airtable account | Free tier works for POC |
| Airtable base | Create one at airtable.com or use an existing base |
| Airtable Personal Access Token | See step 3.1 |
| `pyairtable>=2.3.0` installed | Already in `requirements.txt` |

---

## 3. Airtable Setup

### 3.1 Create a Personal Access Token

1. Go to **airtable.com/create/tokens**
2. Click **+ Add a token**
3. Name it `engineerai-sync`
4. Under **Scopes**, add:
   - `data.records:read`
   - `data.records:write`
5. Under **Access**, select the base you want to sync to
6. Click **Create token** and copy the value — you will not see it again

### 3.2 Create or Identify Your Incidents Table

The integration writes to a single Airtable table. You can use an existing
table or create a new one called **Incidents**.

Required fields — create these if they do not already exist:

| Field name | Airtable field type | Notes |
|---|---|---|
| `Title` | Single line text | Primary field (usually already exists) |
| `Severity` | Single line text | SEV1 / SEV2 / SEV3 / SEV4 |
| `Status` | Single line text | Open / Resolved / etc. |
| `Services Affected` | Single line text | Comma-separated list |
| `Executive Summary` | Long text | AI-generated postmortem summary |
| `Root Cause Analysis` | Long text | AI-generated RCA |
| `Action Items` | Long text | Numbered list with assignee + priority |
| `Occurred At` | Date | ISO-8601 date from the incident |
| `EngineerAI ID` | Single line text | UUID of the incident in EngineerAI |
| `EngineerAI URL` | URL | Deep link back to the incident detail page |

> **Tip:** Field names are case-sensitive. If you rename a field in Airtable,
> you must also update the constant at the top of
> `app/services/airtable_sync.py` — see [section 9](#9-customising-field-names).

### 3.3 Find Your Base ID

1. Open your base in the browser
2. The URL looks like: `https://airtable.com/appXXXXXXXXXXXXXX/...`
3. The `appXXXXXXXXXXXXXX` segment is your **Base ID**

---

## 4. Application Configuration

Add the following to your `.env` file (copy from `.env.example`):

```dotenv
# Airtable incident sync
AIRTABLE_ENABLED=true
AIRTABLE_API_KEY=patXXXXXXXXXXXXXX.XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
AIRTABLE_BASE_ID=appXXXXXXXXXXXXXX
AIRTABLE_TABLE_NAME=Incidents          # must match the table name in Airtable exactly
APP_BASE_URL=http://localhost:8000     # used to build the EngineerAI URL deep link
```

For Kubernetes, add the secret values to `k8s/secret.yaml`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: meetingai-secrets
  namespace: meetingai
type: Opaque
stringData:
  # ... existing keys ...
  AIRTABLE_ENABLED: "true"
  AIRTABLE_API_KEY: "patXXXXXXXXXXXXXX.XXXX..."
  AIRTABLE_BASE_ID: "appXXXXXXXXXXXXXX"
  AIRTABLE_TABLE_NAME: "Incidents"
  APP_BASE_URL: "http://localhost:8000"
```

> **Never commit `k8s/secret.yaml` (or `k8s/secret.local.yaml`) with real
> credentials.** It is listed in `.gitignore` for this reason.

---

## 5. Database Migration

The integration adds an `airtable_record_id` column to the `incidents` table
so the app can update an existing Airtable record on re-processing.

### Docker Compose

```bash
docker compose exec app alembic upgrade head
```

### Kubernetes

Migrations run automatically via the `run-migrations` init container on the
next rollout. After deploying (step 6), check the init container logs:

```bash
kubectl logs -n meetingai deployment/meetingai-app -c run-migrations
```

Expected output includes:

```
Running upgrade 002 -> 003, Add airtable_record_id to incidents ...
Done.
```

### Local (no containers)

```bash
cd meetingai-poc
alembic upgrade head
```

---

## 6. Deploying the Change

### Docker Compose

```bash
docker compose up -d --build
docker compose exec app alembic upgrade head
```

### Kubernetes

```bash
# From meetingai-poc/
docker build -f docker/Dockerfile -t localhost:5001/meetingai-app:latest .
docker push localhost:5001/meetingai-app:latest

kubectl apply -f k8s/secret.yaml          # updated with Airtable keys
kubectl rollout restart deployment/meetingai-app -n meetingai
kubectl rollout status deployment/meetingai-app -n meetingai
```

---

## 7. Verifying the Integration

### Step 1 — Submit a test incident

```bash
curl -s -X POST http://localhost:8000/incidents \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Airtable Sync",
    "severity": "sev3",
    "services_affected": ["api"],
    "description": "API response times exceeded 2s SLO for 10 minutes starting at 14:00 UTC. On-call was paged at 14:03. Root cause was a missing database index on the orders table introduced in deploy v1.4.2. Index was added at 14:22 and latency returned to normal."
  }' | jq .
```

Note the `id` from the response.

### Step 2 — Poll until processing completes

```bash
INCIDENT_ID=<paste id here>
curl -s http://localhost:8000/incidents/$INCIDENT_ID | jq '.processing_status'
# Wait for "completed"
```

### Step 3 — Confirm the record exists in Airtable

Open your Airtable base. A new row should appear in the Incidents table with
all fields populated. The `EngineerAI ID` field should match the UUID above.

### Step 4 — Check application logs

```bash
# Docker Compose
docker compose logs app | grep airtable

# Kubernetes
kubectl logs -n meetingai deployment/meetingai-app | grep airtable
```

Expected log line on success:

```
INFO  app.services.airtable_sync - [airtable] Incident <uuid> synced → record rec<id>
```

---

## 8. Field Reference

| Airtable field | Source in EngineerAI | Example value |
|---|---|---|
| `Title` | `incident.title` | "API latency spike — orders service" |
| `Severity` | `incident.severity` (uppercased) | "SEV2" |
| `Status` | `incident.status` (capitalized) | "Open" |
| `Services Affected` | `incident.services_affected` joined | "api, orders-db" |
| `Executive Summary` | LLM-generated postmortem | "At 14:00 UTC, p99 API latency..." |
| `Root Cause Analysis` | LLM-generated RCA | "A missing index on..." |
| `Action Items` | LLM-extracted, formatted list | "1. [HIGH] Add index → @dba-team" |
| `Occurred At` | `incident.occurred_at` | "2026-04-01T14:00:00+00:00" |
| `EngineerAI ID` | `str(incident.id)` | "a1b2c3d4-..." |
| `EngineerAI URL` | `APP_BASE_URL + /incidents/<id>` | "http://localhost:8000/incidents/a1b2..." |

---

## 9. Customising Field Names

If your Airtable base uses different field names, update the constants at the
top of `app/services/airtable_sync.py`:

```python
_FIELD_TITLE = "Title"             # ← change to match your Airtable column name
_FIELD_SEVERITY = "Severity"
_FIELD_STATUS = "Status"
_FIELD_SERVICES = "Services Affected"
_FIELD_EXEC_SUMMARY = "Executive Summary"
_FIELD_RCA = "Root Cause Analysis"
_FIELD_ACTION_ITEMS = "Action Items"
_FIELD_OCCURRED_AT = "Occurred At"
_FIELD_ENGINEERAI_ID = "EngineerAI ID"
_FIELD_ENGINEERAI_URL = "EngineerAI URL"
```

No other changes are needed — the constants are the only place field names
appear in the code.

---

## 10. Troubleshooting

### Airtable push silently does nothing

1. Confirm `AIRTABLE_ENABLED=true` — check with:
   ```bash
   curl -s http://localhost:8000/health | jq .
   # or grep the running env
   docker compose exec app env | grep AIRTABLE
   ```
2. Confirm `pyairtable` is installed:
   ```bash
   docker compose exec app pip show pyairtable
   ```

### `WARNING [airtable] Failed to sync incident <id>: ...`

The warning message includes the underlying error. Common causes:

| Error text | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | Wrong or expired API key | Regenerate token at airtable.com/create/tokens |
| `404 Not Found` | Wrong `AIRTABLE_BASE_ID` or table name | Verify the base ID from the URL and table name matches exactly |
| `422 INVALID_FIELD_NAME` | Airtable field doesn't exist or name mismatch | Check [section 9](#9-customising-field-names) |
| `Connection refused` | Network issue (e.g., in air-gapped env) | Check outbound HTTPS to `api.airtable.com` |

### Records are being duplicated

This means the `airtable_record_id` was not saved on the first push. Check
the logs from the first run for a warning — it likely means the first push
failed silently (see above). Once fixed, you can manually set the record ID:

```bash
# Connect to the DB and patch the column
docker compose exec db psql -U meetingai -d meetingai -c \
  "UPDATE incidents SET airtable_record_id = 'recXXXXXXXXXXXXXX' WHERE id = '<uuid>';"
```

### Migration fails with "column already exists"

The migration was already applied manually. Run:

```bash
alembic stamp 003
```

---

## 11. Disabling the Integration

Set `AIRTABLE_ENABLED=false` (or remove it — `false` is the default) and
restart the app. No migration rollback is needed; the `airtable_record_id`
column remains in the schema but is never written to.

To fully remove the column:

```bash
alembic downgrade 002
```

This will drop `airtable_record_id` and its index from the `incidents` table.
