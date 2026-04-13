# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

**EngineerAI** — an AI engineering assistant that transcribes meeting recordings, analyzes production incidents, indexes knowledge-base documents, and answers questions across all three using RAG. The app has a React frontend, FastAPI backend, pgvector for semantic search, and a bidirectional Slack bot.

## Development Commands

All commands run from `meetingai-poc/` (this directory).

```bash
# Run the API
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run tests (suite dirs exist but most tests are not yet written)
pytest
pytest -v tests/

# Frontend dev server (proxies API calls to localhost:8000)
cd frontend && npm install && npm run dev   # Vite at localhost:5173

# Build frontend for embedding into the FastAPI static mount
cd frontend && npm run build

# Create a new migration (requires a running DB)
alembic revision --autogenerate -m "description"
```

API docs: `http://localhost:8000/docs`

## Kubernetes Deployment (primary)

Uses Docker Desktop with Kubernetes. Requires a local registry on port 5001:

```bash
docker run -d -p 5001:5000 --restart=always --name local-registry registry:2
```

```bash
# Build and push
docker build -f docker/Dockerfile -t meetingai-app:latest .
docker tag meetingai-app:latest localhost:5001/meetingai-app:latest
docker push localhost:5001/meetingai-app:latest

# Fill in your Anthropic API key in k8s/secret.yaml, then apply
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/app.yaml

kubectl rollout status deployment/meetingai-app -n meetingai
```

Migrations run automatically as a Kubernetes init container. App available at `http://localhost:8000`.

**Redeploy after changes:**
```bash
docker build -f docker/Dockerfile -t localhost:5001/meetingai-app:latest . && docker push localhost:5001/meetingai-app:latest
kubectl rollout restart deployment/meetingai-app -n meetingai
```

**Debug:**
```bash
kubectl get pods -n meetingai
kubectl logs -n meetingai deployment/meetingai-app
kubectl logs -n meetingai deployment/meetingai-app -c run-migrations
kubectl exec -it -n meetingai deployment/meetingai-app -- /bin/bash
```

## Configuration

Only `ANTHROPIC_API_KEY` is required. Copy `.env.example` → `.env` and set it.

Key settings (`app/config/settings.py`):

| Variable | Default | Notes |
|----------|---------|-------|
| `ANTHROPIC_API_KEY` | — | Required |
| `DATABASE_URL` | `postgresql+asyncpg://meetingai:meetingai@localhost:5432/meetingai` | |
| `SUMMARIZATION_MODEL` | `claude-sonnet-4-6` | Used for summaries, Q&A |
| `EXTRACTION_MODEL` | `claude-haiku-4-5-20251001` | Used for action item / incident extraction |
| `WHISPER_MODE` | `local` | `local` = faster-whisper (CPU); `api` = OpenAI API |
| `WHISPER_MODEL` | `base` | `tiny`/`base`/`small`/`medium`/`large` |
| `SLACK_ENABLED` | `false` | `false` = MockSlackClient logs to stdout |

## Architecture

### Request Flows

```
POST /meetings/upload
  → save file + DB record
  → BackgroundTask: ProcessingService
      1. TranscriptionService  → faster-whisper (local CPU) → transcript + segments
      2. SummarizationService  → Claude (concurrent asyncio.gather) → summary, action items, decisions
      3. EmbeddingService      → chunk transcript → sentence-transformers → pgvector
      4. SlackClient           → notify channel

POST /incidents  or  POST /incidents/upload
  → create incident + DB record
  → BackgroundTask: IncidentProcessingService
      1. IncidentExtractionService → Claude → postmortem, timeline, action items
      2. EmbeddingService          → chunk incident text → pgvector
      3. SlackClient               → post postmortem summary

POST /knowledge-base/upload
  → save file + DB record
  → BackgroundTask: DocProcessingService → chunk → embed → pgvector

POST /qa  →  RAGQueryService (app/rag/qa.py)
  → embed query → PolymorphicRetriever (pgvector similarity across meetings + incidents + docs)
  → build context → Claude completion

POST /slack/events | /slack/commands | /slack/interactions
  → Slack bot (app_mention, /incident, /ask, /search, /incidents, /meetings)
```

### Layer Responsibilities

| Layer | Path | Role |
|-------|------|------|
| API | `app/api/` | FastAPI routers: `meetings`, `incidents`, `docs`, `search`, `health`, `slack_router` |
| Services | `app/services/` | `processing.py`, `incident_processing.py`, `doc_processing.py`, `transcription.py`, `summarization.py`, `embedding.py`, `incident_extraction.py` |
| LLM | `app/llm/client.py` | `LLMClient`: Anthropic SDK for completions, `sentence-transformers` (lazy-loaded, run in executor) for embeddings |
| Prompts | `app/llm/prompts.py` | All prompt templates |
| RAG | `app/rag/` | `chunker.py` → `retriever.py` (`VectorRetriever` + `PolymorphicRetriever`) → `qa.py` |
| DB | `app/db/repository.py` | All CRUD: `MeetingRepository`, `IncidentRepository`, `DocumentRepository` |
| Models | `app/models/database.py` | SQLAlchemy ORM (14 tables); `schemas.py` for Pydantic DTOs |
| Slack | `app/slack/` | `base.py` → `real.py` / `mock.py`; `factory.py` picks based on `SLACK_ENABLED`; `message_builder.py`, `incident_modal.py` |
| Workers | `app/workers/` | `tasks.py` (meeting/doc background tasks), `slack_tasks.py` |
| Config | `app/config/settings.py` | Pydantic `BaseSettings`, singleton via `get_settings()` |
| Frontend | `frontend/src/` | React 18 + TypeScript + Vite; `api/` (axios clients), `components/`, `hooks/` (TanStack Query + polling), `types/` |

### Database Schema (14 tables)

**Meetings:** `meetings` → `transcripts` + `transcript_segments` → `summaries`, `action_items`, `decisions`, `embedding_chunks`

**Incidents:** `incidents` → `incident_postmortems`, `incident_timeline_events`, `incident_action_items`, `incident_chunks`

**Knowledge Base:** `documents` → `doc_chunks`

All `*_chunks` tables store `pgvector` `Vector(384)` embeddings (384-dim from `all-MiniLM-L6-v2`).

### Frontend ↔ Backend Integration

The Dockerfile does a multi-stage build: Node builds `frontend/dist/`, then the Python image serves it via `StaticFiles` mounted at `/` in `app/main.py`. The API router is mounted before the static mount so `/docs`, `/meetings`, `/qa`, etc. are not intercepted.

During local dev, Vite proxies API calls from `localhost:5173` to `localhost:8000`.

## Intentionally Out of Scope

Live audio streaming, calendar integration, authentication/multi-tenancy, speaker diarization, production retry queues, enterprise SSO.
