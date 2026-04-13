# EngineerAI — AI Engineering Assistant

> An AI-powered engineering assistant that summarizes production incidents, generates draft
> postmortems, answers questions about service architecture, and provides AI-assisted analysis
> across meeting recordings, incidents, and knowledge-base documents.

## What This Does

- **Upload** meeting recordings (audio/video: mp3, wav, mp4, webm, m4a)
- **Transcribe** automatically via faster-whisper (local CPU inference, no API key needed)
- **Summarize** meetings with LLM-generated prose summaries
- **Extract** action items (with assignees) and decisions (with rationale)
- **Log incidents** via form input or file upload (log files, runbooks, descriptions)
- **Analyze incidents** — generates executive summaries, root cause analysis, timelines, and remediation action items
- **Knowledge base** — upload architecture docs and runbooks for RAG-powered Q&A
- **Search & Q&A** across all meetings, incidents, and documents using RAG (pgvector + LLM)
- **Slack notifications** (mocked by default, real integration available)

## Architecture

```
Meetings:  Upload → faster-whisper (transcribe) → Claude (summary + actions + decisions) → pgvector (embed)
Incidents: Create/Upload → Claude (postmortem + timeline + actions) → pgvector (embed)
Docs:      Upload → pgvector (embed)

Search/Q&A: query → embed → pgvector similarity search (meetings + incidents + docs) → Claude (answer)
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18 + TypeScript + Vite |
| API | FastAPI (Python 3.11+) |
| LLM | Anthropic API (Claude) |
| Transcription | faster-whisper (local, CPU, int8) |
| Embeddings | sentence-transformers (local, all-MiniLM-L6-v2) |
| Vector Store | PostgreSQL + pgvector |
| Background Tasks | FastAPI BackgroundTasks |
| Slack | Mock client (real client available) |
| Infrastructure | Kubernetes (Docker Desktop) |

## Quick Start

### Prerequisites

- Docker Desktop with Kubernetes enabled (`docker-desktop` context)
- A local registry running on port 5001:
  ```bash
  docker run -d -p 5001:5000 --restart=always --name local-registry registry:2
  ```
- An Anthropic API key

### Configuration

Copy `.env.example` to `.env` and fill in the required values:

```bash
cp .env.example .env
```

Required variables:

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key (required) |
| `ADMIN_TOKEN` | Secret token to protect `/admin/reset` (required, choose any strong value) |

Optional variables with defaults:

| Variable | Default | Description |
|----------|---------|-------------|
| `SUMMARIZATION_MODEL` | `claude-sonnet-4-6` | Model for summaries and Q&A |
| `EXTRACTION_MODEL` | `claude-haiku-4-5-20251001` | Model for action item / incident extraction |
| `WHISPER_MODE` | `local` | `local` (faster-whisper CPU) or `api` (OpenAI API) |
| `WHISPER_MODEL` | `base` | `tiny` / `base` / `small` / `medium` / `large` |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Comma-separated CORS-allowed origins |
| `PROCESSING_TIMEOUT_SECONDS` | `1800` | Max time (seconds) for a background processing job |
| `SLACK_ENABLED` | `false` | Set `true` to use a real Slack workspace |

### Deploy to Kubernetes

Secrets are injected from your shell environment — no keys are stored in YAML files.

```bash
# 1. Build the image (ML models are pre-downloaded into the image layer)
docker build -f docker/Dockerfile -t meetingai-app:latest .
docker tag meetingai-app:latest localhost:5001/meetingai-app:latest
docker push localhost:5001/meetingai-app:latest

# 2. Export your secrets as environment variables
export ANTHROPIC_API_KEY=sk-ant-...
export ADMIN_TOKEN=your-strong-token          # protects POST /admin/reset
# Optional — only needed if enabling Slack:
# export SLACK_BOT_TOKEN=xoxb-...
# export SLACK_SIGNING_SECRET=...

# 3. Run the deploy script (applies all manifests in the correct order)
./scripts/k8s-apply.sh
```

The script validates that required env vars are set, renders `k8s/secret.yaml` via `envsubst`, applies all manifests, and waits for the rollout.

Alternatively, apply manually:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
envsubst < k8s/secret.yaml | kubectl apply -f -   # renders ${VAR} placeholders
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/app.yaml
kubectl rollout status deployment/meetingai-app -n meetingai
```

The app is available at **http://localhost:8000** once the rollout completes.

### Redeploying after code changes

```bash
docker build -f docker/Dockerfile -t localhost:5001/meetingai-app:latest .
docker push localhost:5001/meetingai-app:latest
kubectl rollout restart deployment/meetingai-app -n meetingai
```

> Secrets do not need to be re-applied on a code-only redeploy — only run `envsubst < k8s/secret.yaml | kubectl apply -f -` again if the secret values themselves change.

### Run locally (no containers)

```bash
# Copy and edit your .env
cp .env.example .env

# Start the API (requires a running PostgreSQL with pgvector)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend dev server (proxies API calls to localhost:8000)
cd frontend && npm install && npm run dev   # Vite at localhost:5173
```

## Using the UI

Open **http://localhost:8000** for the full React frontend.

### Meetings

- **Upload Recording** — attach an audio/video file, add a title and optional participants
- **Processing** — the app transcribes, summarizes, and embeds the recording in the background; a banner shows progress and disappears when complete
- **Meeting detail** — four tabs: Summary, Transcript (speaker-labeled segments), Action Items, Decisions

### Incidents

- **Log Incident** — click the alert icon in the sidebar Incidents section. Two options:
  - **Describe tab** — paste an incident description, error messages, or log output directly into the form
  - **Upload File tab** — attach a log file or runbook (`.txt`, `.md`, `.log`, `.json`, `.yaml`, `.py`)
- **Analysis** — the app generates a postmortem (executive summary + root cause analysis), a timeline of events, and remediation action items in the background
- **Incident detail** — three tabs: Postmortem, Timeline, Action Items

### Knowledge Base

- **Add Document** — click the document icon in the Knowledge Base section to upload architecture docs, runbooks, or API references
- **Indexing** — documents are chunked and embedded for RAG retrieval

### Search / Ask

- **Chat panel** — Q&A (synthesized answer) and Search (chunk result cards) modes via toggle
- **Scope selector** — ask across all sources or scope to a specific meeting, incident, or document
- **Sources** — collapsible source citations show which meeting/incident/document each answer drew from

API docs (Swagger UI) remain available at **http://localhost:8000/docs**.

### Notes on transcription

- **Model pre-baked** — the Whisper model is downloaded into the Docker image at build time; the first request does not incur a download delay
- **Transcription accuracy** with the `base` model is good for clear speech; for technical vocabulary or accents, change `WHISPER_MODEL=small` in `k8s/configmap.yaml` and rebuild the image
- **Transcription speed** is CPU-only and roughly real-time (1× speed), so a 10-minute recording takes ~10 minutes to transcribe

### Frontend development (without rebuilding Docker)

```bash
cd frontend
npm install
npm run dev   # Vite dev server at localhost:5173, proxies API calls to localhost:8000
```

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/meetings/upload` | POST | Upload a meeting recording (rate limited: 10/min) |
| `/meetings/{id}/process` | POST | Trigger processing pipeline |
| `/meetings/{id}` | GET | Get meeting details with transcript, summary, etc. |
| `/meetings` | GET | List all meetings (paginated) |
| `/incidents` | POST | Create an incident from form input (rate limited: 10/min) |
| `/incidents/upload` | POST | Upload an incident log file (rate limited: 10/min) |
| `/incidents/{id}` | GET | Get incident details with postmortem, timeline, etc. |
| `/incidents` | GET | List all incidents (paginated) |
| `/knowledge-base/upload` | POST | Upload a knowledge-base document (rate limited: 10/min) |
| `/knowledge-base/{id}` | GET | Get document details |
| `/knowledge-base` | GET | List all documents (paginated) |
| `/search` | POST | Semantic search across meetings, incidents, and docs (rate limited: 60/min) |
| `/qa` | POST | Ask a question using RAG (rate limited: 60/min) |
| `/slack/events` | POST | Slack Events API (app_mention → RAG answer) |
| `/slack/commands` | POST | Slash commands dispatcher |
| `/slack/interactions` | POST | Modal submissions and button callbacks |
| `/health` | GET | Health check (DB connectivity + LLM config) |
| `/metrics` | GET | Prometheus metrics endpoint |
| `/admin/reset` | POST | Truncate all tables and delete uploaded files — **requires auth** |

> **Note:** `/knowledge-base` is used instead of `/docs` because FastAPI reserves `/docs` for its built-in Swagger UI.

## Resetting the Database (Admin)

The `/admin/reset` endpoint wipes all data and uploaded files. It is protected by a bearer token:

```bash
# Using curl
curl -X POST http://localhost:8000/admin/reset \
  -H "Authorization: Bearer <your-ADMIN_TOKEN>"

# Or use Swagger UI at http://localhost:8000/docs → POST /admin/reset
# Click "Authorize" and enter your token first
```

The value of `ADMIN_TOKEN` is set in your `.env` (local) or `k8s/secret.yaml` (Kubernetes).

## Security

| Feature | Details |
|---------|---------|
| Admin endpoint protection | `POST /admin/reset` requires `Authorization: Bearer <ADMIN_TOKEN>` |
| CORS | Restricted to origins listed in `ALLOWED_ORIGINS` |
| Rate limiting | Upload endpoints: 10 req/min per IP; search/QA: 60 req/min per IP |
| Key validation | App refuses to start if `ANTHROPIC_API_KEY` or `ADMIN_TOKEN` are not set |
| Error responses | Unhandled exceptions return a generic 500 — no stack traces in responses |

## Observability

| Feature | Details |
|---------|---------|
| Prometheus metrics | Available at `GET /metrics` — auto-instrumented HTTP latency/throughput histograms |
| Custom counters | `meeting_processing_total{status}` (success/failed/timeout) |
| Custom histograms | `meeting_processing_duration_seconds` |
| Request tracing | Every request gets a `X-Request-ID` header (generated if absent, echoed in response) |
| Structured logging | JSON-structured logs include `meeting_id`/`incident_id` on service-level log lines |

To scrape metrics with Prometheus, the K8s deployment includes standard annotations:
```yaml
prometheus.io/scrape: "true"
prometheus.io/port: "8000"
prometheus.io/path: "/metrics"
```

## Running Tests

```bash
# Install dev dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run the full test suite
pytest tests/ -v

# Run a specific test file
pytest tests/test_api/test_admin.py -v

# Lint
ruff check app/ tests/
```

Tests require a running PostgreSQL instance. Set `DATABASE_URL` to point at a test database, or use Docker Compose:

```bash
docker compose up -d db
DATABASE_URL=postgresql+asyncpg://meetingai:meetingai@localhost:5432/meetingai \
ANTHROPIC_API_KEY=test \
ADMIN_TOKEN=test \
pytest tests/ -v
```

CI runs automatically on every push and pull request via `.github/workflows/ci.yml`.

## Slack Integration

The app includes a **bidirectional Slack bot** — an alternative to the web UI that lets engineers log incidents, run searches, and ask questions without leaving Slack.

**Default (mock):** All Slack messages are logged to stdout. The three `/slack/*` endpoints are always available but signature verification is skipped when `SLACK_SIGNING_SECRET` is not set.

### Slash Commands

| Command | What it does |
|---------|-------------|
| `/incident [text]` | Opens a modal to log an incident; text pre-fills the description |
| `/ask <question>` | RAG Q&A across all meetings, incidents, and docs |
| `/search <query>` | Semantic search — returns top 5 results with excerpts |
| `/incidents` | Lists the 5 most recent incidents |
| `/meetings` | Lists the 5 most recent meetings |

**App mention:** `@EngineerAI <question>` answers in-thread using the same RAG pipeline.

**Proactive notifications:** when an incident's AI analysis completes, the bot posts the postmortem summary to the originating channel.

### Enabling the Real Bot

1. Create a Slack App at https://api.slack.com/apps → **From scratch**
2. **Slash Commands** → add `/incident`, `/ask`, `/search`, `/incidents`, `/meetings` all pointing to `https://<host>/slack/commands`
3. **Event Subscriptions** → enable, URL: `https://<host>/slack/events`, subscribe bot event: `app_mention`
4. **Interactivity & Shortcuts** → enable, URL: `https://<host>/slack/interactions`
5. **OAuth & Permissions** → Bot Token Scopes: `chat:write`, `chat:write.public`, `commands`, `im:write`, `views:open`
6. Install to workspace → copy **Bot User OAuth Token** → `SLACK_BOT_TOKEN`
7. Copy **Signing Secret** → `SLACK_SIGNING_SECRET`
8. Export `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET` and re-run `envsubst < k8s/secret.yaml | kubectl apply -f -`
9. Update `k8s/configmap.yaml`: set `SLACK_ENABLED=true` and `SLACK_DEFAULT_CHANNEL`
10. Redeploy: `kubectl rollout restart deployment/meetingai-app -n meetingai`

For local development, expose the app with `ngrok http 8000` and use the ngrok URL as the Request URL above.

## Project Structure

```
meetingai-poc/
├── app/
│   ├── main.py              # FastAPI app entry point, middleware, Prometheus, rate limiter
│   ├── api/                 # Route handlers (meetings, incidents, docs, search, health, slack, admin)
│   ├── config/              # Pydantic settings with startup validation
│   ├── db/                  # SQLAlchemy session + repository (Meeting, Incident, Document)
│   ├── llm/                 # LLM client (Anthropic, with retry) + prompt templates
│   ├── models/              # ORM models + Pydantic schemas
│   ├── rag/                 # Chunker, retriever (VectorRetriever + PolymorphicRetriever), Q&A pipeline
│   ├── services/            # Transcription, summarization, embedding, processing, incident/doc processing
│   ├── slack/               # Slack client (real + mock + factory + message_builder + incident_modal)
│   └── workers/             # Background tasks with timeouts, metrics, and failure visibility
├── frontend/                # React + TypeScript + Vite frontend
│   └── src/
│       ├── api/             # Axios API client (meetings, incidents, docs, search)
│       ├── components/      # UI components (layout, meetings, incidents, docs, chat)
│       ├── hooks/           # TanStack Query hooks + polling logic
│       └── types/           # TypeScript interfaces mirroring API schemas
├── migrations/              # Alembic database migrations
├── tests/                   # Test suite (API, services, RAG)
│   ├── conftest.py          # Shared fixtures (async client, admin headers)
│   ├── test_api/            # Endpoint integration tests (admin auth, meetings, health)
│   ├── test_services/       # Service unit tests (summarization JSON parsing, pipeline)
│   └── test_rag/            # RAG pipeline unit tests
├── .github/workflows/       # GitHub Actions CI (lint + test on push/PR)
├── docker/                  # Dockerfile (multi-stage: Node build + Python runtime + model pre-download)
├── k8s/                     # Kubernetes manifests (with resource limits and Prometheus annotations)
├── pyproject.toml           # Ruff, mypy, pytest configuration
├── requirements.txt         # Production dependencies
├── requirements-dev.txt     # Dev/test-only dependencies
└── .env.example             # Annotated environment variable template
```

## Intentionally Out of Scope

- User authentication / multi-tenancy (no login, all data is shared)
- Live meeting bots / real-time transcription
- Calendar integration (Google Calendar, Outlook)
- Speaker diarization (best-effort labels only)
- Enterprise SSO / RBAC
- Production retry queues (background tasks run in-process)
