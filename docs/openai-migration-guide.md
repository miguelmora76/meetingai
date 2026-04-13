# OpenAI Migration Guide

This guide covers everything required to switch the EngineerAI backend from the
Anthropic API to your company's existing OpenAI API key. It includes every file
that needs to change, the exact edits to make, configuration steps, and a
decision point around embeddings that has database implications.

---

## Table of Contents

1. [What Changes vs. What Stays the Same](#1-what-changes-vs-what-stays-the-same)
2. [Prerequisites](#2-prerequisites)
3. [Step 1 — Update `app/llm/client.py`](#3-step-1--update-appllmclientpy)
4. [Step 2 — Update `app/config/settings.py`](#4-step-2--update-appconfigsettingspy)
5. [Step 3 — Update Environment Variables](#5-step-3--update-environment-variables)
6. [Step 4 — Update `requirements.txt`](#6-step-4--update-requirementstxt)
7. [Embeddings Decision](#7-embeddings-decision)
8. [Model Name Reference](#8-model-name-reference)
9. [Verifying the Migration](#9-verifying-the-migration)
10. [Rollback](#10-rollback)

---

## 1. What Changes vs. What Stays the Same

### Changes

| Component | File | What changes |
|-----------|------|-------------|
| Chat completions | `app/llm/client.py` | SDK call switches from `anthropic.AsyncAnthropic` to `openai.AsyncOpenAI`; response parsing changes |
| Default model names | `app/config/settings.py` | `claude-*` → `gpt-4o` / `gpt-4o-mini` |
| Environment variables | `.env` | `ANTHROPIC_API_KEY` → `OPENAI_API_KEY` (already exists in settings); new model name defaults |
| Dependencies | `requirements.txt` | `anthropic` package can be removed |

### Does NOT change (no edits needed)

| Component | Reason |
|-----------|--------|
| `app/llm/prompts.py` | All prompts are plain-text system/user pairs with no vendor-specific syntax |
| `app/services/transcription.py` | Whisper API mode already uses `openai.AsyncOpenAI`; local mode uses `faster-whisper` |
| `app/services/summarization.py` | Calls `llm.complete()` by name — unaffected by what's under the hood |
| `app/services/incident_processing.py` | Same — uses `LLMClient` interface only |
| `app/services/incident_extraction.py` | Same |
| `app/rag/` | Unaffected |
| `app/db/`, `app/models/`, `app/api/` | Unaffected |
| `app/slack/` | Unaffected |
| `app/services/airtable_sync.py` | Unaffected |
| Embeddings (default) | See [section 7](#7-embeddings-decision) — local `sentence-transformers` is the recommended default and requires no change |

---

## 2. Prerequisites

- A valid OpenAI API key with access to `gpt-4o` and `gpt-4o-mini` (or whichever models your company has enabled)
- The `openai` Python package — already in `requirements.txt`
- No database migration is required unless you also switch embeddings to OpenAI (see section 7)

---

## 3. Step 1 — Update `app/llm/client.py`

This is the only Python file that references the Anthropic SDK. Replace the
`complete()` method body.

**Current implementation (Anthropic):**

```python
async def complete(
    self,
    model: str,
    system: str,
    user: str,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    response_format: dict | None = None,
) -> str:
    import anthropic

    logger.info(f"LLM request: model={model}, system_len={len(system)}, user_len={len(user)}")

    client = anthropic.AsyncAnthropic(api_key=self.settings.anthropic_api_key)
    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        temperature=temperature,
    )
    content = response.content[0].text

    logger.info(
        f"LLM response: model={model}, "
        f"input_tokens={response.usage.input_tokens if response.usage else '?'}, "
        f"output_tokens={response.usage.output_tokens if response.usage else '?'}"
    )

    return content
```

**Replace with (OpenAI):**

```python
async def complete(
    self,
    model: str,
    system: str,
    user: str,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    response_format: dict | None = None,
) -> str:
    from openai import AsyncOpenAI

    logger.info(f"LLM request: model={model}, system_len={len(system)}, user_len={len(user)}")

    client = AsyncOpenAI(api_key=self.settings.openai_api_key)

    kwargs = dict(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
    )
    if response_format:
        kwargs["response_format"] = response_format

    response = await client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content

    logger.info(
        f"LLM response: model={model}, "
        f"input_tokens={response.usage.prompt_tokens if response.usage else '?'}, "
        f"output_tokens={response.usage.completion_tokens if response.usage else '?'}"
    )

    return content
```

### Key API differences explained

| Concept | Anthropic | OpenAI |
|---------|-----------|--------|
| Client class | `anthropic.AsyncAnthropic` | `openai.AsyncOpenAI` |
| API key setting | `self.settings.anthropic_api_key` | `self.settings.openai_api_key` |
| System prompt | Top-level `system=` parameter | First message: `{"role": "system", "content": ...}` |
| Completion call | `client.messages.create(...)` | `client.chat.completions.create(...)` |
| Response text | `response.content[0].text` | `response.choices[0].message.content` |
| Input token count | `response.usage.input_tokens` | `response.usage.prompt_tokens` |
| Output token count | `response.usage.output_tokens` | `response.usage.completion_tokens` |
| JSON mode | Not a parameter (prompt-enforced) | `response_format={"type": "json_object"}` |

> **Note on JSON mode:** The Anthropic client previously accepted `response_format`
> as a parameter but silently ignored it — the JSON output worked purely because
> the prompts say "Respond with valid JSON only." OpenAI's JSON mode is now
> **actually enforced** when you pass `response_format={"type": "json_object"}`,
> which means OpenAI will guarantee a parseable JSON response. This is a strict
> improvement; no prompt changes are needed.

---

## 4. Step 2 — Update `app/config/settings.py`

Change the default model names. The `openai_api_key` field already exists in
settings — only the defaults for `summarization_model` and `extraction_model`
need updating.

**Find these lines:**

```python
summarization_model: str = "claude-sonnet-4-6"
extraction_model: str = "claude-haiku-4-5-20251001"
```

**Change to:**

```python
summarization_model: str = "gpt-4o"
extraction_model: str = "gpt-4o-mini"
```

The `anthropic_api_key` field can be left in place (it defaults to `""` and is
now unused) or removed — removing it avoids confusion but is optional.

---

## 5. Step 3 — Update Environment Variables

### Local `.env`

```dotenv
# Remove or leave blank — no longer used
ANTHROPIC_API_KEY=

# Set your company's OpenAI key
OPENAI_API_KEY=sk-proj-your-key-here

# Update model names (or omit to use the new defaults from step 2)
SUMMARIZATION_MODEL=gpt-4o
EXTRACTION_MODEL=gpt-4o-mini

# Whisper — switch to API mode to use the same OpenAI key
WHISPER_MODE=api
```

### Kubernetes `k8s/secret.yaml`

```yaml
stringData:
  ANTHROPIC_API_KEY: ""          # blank it out or remove the entry
  OPENAI_API_KEY: "sk-proj-..."  # your company key
  SUMMARIZATION_MODEL: "gpt-4o"
  EXTRACTION_MODEL: "gpt-4o-mini"
  WHISPER_MODE: "api"
```

After updating the secret, redeploy:

```bash
kubectl apply -f k8s/secret.yaml
kubectl rollout restart deployment/meetingai-app -n meetingai
```

---

## 6. Step 4 — Update `requirements.txt`

The `openai` package is already present. The `anthropic` package is no longer
needed for completions. Remove it to avoid an unnecessary dependency:

**Find and remove:**

```
anthropic>=0.40.0
```

The `openai` line stays as-is:

```
openai>=1.12.0
```

If you have a running container, rebuild after this change:

```bash
# Docker Compose
docker compose up -d --build

# Kubernetes
docker build -f docker/Dockerfile -t localhost:5001/meetingai-app:latest .
docker push localhost:5001/meetingai-app:latest
kubectl rollout restart deployment/meetingai-app -n meetingai
```

---

## 7. Embeddings Decision

This is the only decision point with database implications. You have two options:

### Option A — Keep local sentence-transformers (recommended)

**No code changes. No DB migration. No OpenAI cost.**

The embedding model (`all-MiniLM-L6-v2`, running locally) is completely
independent of the LLM provider. It produces 384-dimensional vectors, which is
what the current `pgvector` schema stores (`Vector(384)`). Keeping it means:

- Zero additional API cost per document/query
- No re-embedding of existing data
- Works offline / in air-gapped environments
- Slightly lower retrieval quality than OpenAI embeddings, but adequate for this use case

This is the default and the recommended path.

### Option B — Switch to OpenAI embeddings (`text-embedding-3-small`)

Only consider this if you need higher semantic accuracy for the RAG Q&A feature.

**Implications:**

| Impact | Detail |
|--------|--------|
| Vector dimension changes | `text-embedding-3-small` outputs **1536** dimensions; current schema stores **384** |
| DB migration required | Must drop and recreate all `*_chunks` tables or alter their `embedding` column |
| Re-embedding required | All existing meeting, incident, and doc chunks must be re-embedded with the new model |
| Ongoing API cost | Every new upload and every search query will call the OpenAI embeddings API |
| `sentence-transformers` can be removed | Saves ~500 MB from the Docker image |

**If you choose Option B, the changes are:**

1. **`app/llm/client.py` — replace `embed()`:**

   ```python
   async def embed(self, texts: list[str]) -> list[list[float]]:
       from openai import AsyncOpenAI
       logger.info(f"Embedding request: {len(texts)} texts")
       client = AsyncOpenAI(api_key=self.settings.openai_api_key)
       response = await client.embeddings.create(
           model=self.settings.embedding_model,
           input=texts,
       )
       return [item.embedding for item in response.data]
   ```

2. **`app/config/settings.py`:**

   ```python
   embedding_model: str = "text-embedding-3-small"   # was "all-MiniLM-L6-v2"
   ```

3. **DB migration** — change `Vector(384)` → `Vector(1536)` in all three chunk tables and re-embed everything. This is a destructive operation on existing data; plan a maintenance window.

4. **`requirements.txt`** — remove `sentence-transformers>=2.7.0` and `faster-whisper` can stay.

**Bottom line:** Unless the team is specifically unhappy with RAG answer quality, choose Option A. The switch can always be made later.

---

## 8. Model Name Reference

| Role | Current (Anthropic) | Recommended (OpenAI) | Notes |
|------|--------------------|-----------------------|-------|
| Summaries, postmortems, Q&A | `claude-sonnet-4-6` | `gpt-4o` | Highest quality; most expensive |
| Action items, decisions, timeline extraction | `claude-haiku-4-5-20251001` | `gpt-4o-mini` | Fast and cheap; adequate for structured JSON extraction |
| Embeddings (if switching) | `all-MiniLM-L6-v2` (local) | `text-embedding-3-small` | See section 7 |
| Transcription (API mode) | — | `whisper-1` | Hardcoded in `transcription.py`; no change needed |

If your company's OpenAI subscription has different model access, substitute accordingly. The model names are env-var controlled — no code change needed to swap between e.g. `gpt-4o` and `gpt-4-turbo`.

---

## 9. Verifying the Migration

### Health check

```bash
curl -s http://localhost:8000/health | jq .
```

### Test a meeting summary (end-to-end LLM call)

```bash
# Submit a short text incident (faster than audio transcription for testing)
curl -s -X POST http://localhost:8000/incidents \
  -H "Content-Type: application/json" \
  -d '{
    "title": "OpenAI migration smoke test",
    "severity": "sev4",
    "description": "Brief test to confirm OpenAI integration is working. No real incident."
  }' | jq .id
```

Poll until `processing_status` is `"completed"`:

```bash
curl -s http://localhost:8000/incidents/<id> | jq '{status: .processing_status, summary: .postmortem.executive_summary}'
```

### Check logs for OpenAI calls

```bash
# Docker Compose
docker compose logs app | grep "LLM request\|LLM response"

# Kubernetes
kubectl logs -n meetingai deployment/meetingai-app | grep "LLM request\|LLM response"
```

You should see log lines referencing `gpt-4o` and `gpt-4o-mini` (or whichever
models you configured), with `input_tokens` and `output_tokens` counts.

### Confirm no Anthropic calls are being made

```bash
grep -r "anthropic" app/ --include="*.py"
```

After the migration, the only remaining reference should be the (now-unused)
`anthropic_api_key` field in `settings.py`. There should be **no** `import anthropic`
anywhere.

---

## 10. Rollback

If you need to revert to Anthropic:

1. Restore the original `complete()` body in `app/llm/client.py` (or keep both and toggle via a `LLM_PROVIDER` env var if you want to make the choice runtime-configurable)
2. Set `ANTHROPIC_API_KEY` back in `.env` / Kubernetes secret
3. Restore `summarization_model` and `extraction_model` to their `claude-*` defaults
4. Re-add `anthropic>=0.40.0` to `requirements.txt`
5. Rebuild and redeploy

No database changes are needed for rollback (unless you also switched embeddings).
