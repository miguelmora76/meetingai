# Airtable User Connection & Import

Companion to [`airtable-integration.md`](./airtable-integration.md). That file covers the **server-side push sync** that fires automatically when meetings/incidents/docs finish processing. This file covers the **user-driven pull flow**: a user connects their own Airtable account from the frontend and imports a table into the knowledge base, so the RAG pipeline can answer questions across it.

This is a single-user POC integration — exactly one Airtable connection is stored, keyed by `user_id='default'`. The schema and design are forward-compatible with a real multi-user layer if one is added later.

---

## One-time setup

### 1. Generate a Fernet encryption key

User PATs are encrypted at rest. Generate a key once and keep it stable — rotating it invalidates the stored token and forces a reconnect.

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 2. Configure the environment

Add to `.env` (local dev) or `k8s/secret.yaml` (Kubernetes):

```
AIRTABLE_TOKEN_ENCRYPTION_KEY=<the-key-from-step-1>
```

The `cryptography` package is already pinned in `requirements.txt`.

### 3. Run the migration

The migration is picked up automatically by the k8s init container or by `alembic upgrade head` locally.

```bash
alembic upgrade head
```

This creates:

- `airtable_connections` — one-row table storing the encrypted PAT, Airtable user id/email, and granted scopes.
- `airtable_imports` — per-import progress tracking (status, records total/processed, documents created, error).
- `documents.airtable_source_ref` — JSONB column on existing `documents`, populated for rows imported from Airtable. Used to upsert on re-import instead of creating duplicates.

---

## Using it

1. **Create a PAT** at [airtable.com/create/tokens](https://airtable.com/create/tokens). Required scopes:
   - `data.records:read`
   - `schema.bases:read`
   - `user.email:read` (optional but nice — surfaces the email on the connection pill)

   Grant the token access to the bases you want to import.

2. **Connect from the frontend.** Open the app — the sidebar header shows a **"Connect Airtable"** pill. Click it, paste the token, submit. The backend validates it against Airtable's `/meta/whoami` and stores it encrypted.

3. **Import a table.** Once connected, the Knowledge Base section header gains a database icon. Click it to open the import wizard:
   - **Base** — pick from the bases your token can access.
   - **Table** — pick a table in that base.
   - **Fields** — pick which field becomes the document title (defaults to the primary field), and check which fields to render into the document body (defaults to all text-like fields).
   - **Import** — progress polls every 1.5s. Each imported record becomes one `Document` row with `doc_type='airtable'`, gets chunked + embedded by the existing `DocProcessingService`, and immediately becomes available to RAG search and Q&A.

4. **Re-importing.** Running the same table import again updates existing documents in place (matched via `airtable_source_ref.base_id` + `record_id`) and re-embeds them. Records deleted in Airtable are not deleted from the knowledge base.

5. **Disconnecting.** Click the connected-email pill → "Disconnect." This removes the stored credential but leaves already-imported documents intact.

---

## Architecture

### Request flows

```
POST /airtable/connect
  → AirtableConnectionService.validate_token()  (calls api.airtable.com/v0/meta/whoami)
  → fernet-encrypt PAT → upsert airtable_connections row
  → return connection metadata (email, scopes, missing_required_scopes)

GET  /airtable/connection              → read airtable_connections (no token returned)
DELETE /airtable/connection            → remove row

GET  /airtable/bases                   → Airtable meta /bases
GET  /airtable/bases/{id}/tables       → Airtable meta /bases/{id}/tables

POST /airtable/import
  → insert airtable_imports row (status='pending')
  → BackgroundTask: airtable_import_task
      1. Decrypt PAT from airtable_connections
      2. pyairtable.table.all() (in asyncio.to_thread)
      3. For each record: upsert Document with airtable_source_ref JSON
      4. For each Document: DocProcessingService (chunk → sentence-transformers → pgvector)
      5. Update airtable_imports progress as it goes

GET  /airtable/imports/{id}            → poll progress
```

### Layer responsibilities

| Concern | File |
|---|---|
| Connect/list/delete endpoints | `app/api/airtable_connection_router.py` |
| Bases/tables/import endpoints | `app/api/airtable_router.py` (also still hosts the existing webhook) |
| PAT validation + encryption + storage | `app/services/airtable_connection.py` |
| Table → documents import | `app/services/airtable_import.py` |
| Background task wrapper (timeout + failure handling) | `app/workers/tasks.py::airtable_import_task` |
| Document chunk + embed (unchanged, reused) | `app/services/doc_processing.py` |
| ORM models | `app/models/database.py` (`AirtableConnection`, `AirtableImport`, `Document.airtable_source_ref`) |
| Pydantic DTOs | `app/models/schemas.py` (`AirtableConnect*`, `AirtableBase*`, `AirtableImport*`) |
| Repository upsert-by-record | `app/db/repository.py::DocumentRepository.find_document_by_airtable_record` |
| Migration | `migrations/versions/006_airtable_user_connection.py` |
| Settings | `app/config/settings.py::airtable_token_encryption_key` |

### Frontend

| Concern | File |
|---|---|
| Axios calls | `frontend/src/api/airtable.ts` |
| TanStack Query hooks (incl. progress polling) | `frontend/src/hooks/useAirtable.ts` |
| Sidebar header pill (connect / connected / scope warnings / disconnect menu) | `frontend/src/components/airtable/AirtableConnectionPill.tsx` |
| Connect dialog (masked PAT input + required-scopes list) | `frontend/src/components/airtable/ConnectAirtableDialog.tsx` |
| Import wizard (4 steps: base → table → fields → progress) | `frontend/src/components/airtable/AirtableImportDialog.tsx` |
| Airtable badge on imported docs | `frontend/src/components/docs/DocListItem.tsx` |
| Types | `frontend/src/types/api.ts` |

---

## Security notes

- **Tokens are encrypted at rest** with Fernet (symmetric AES-128-CBC + HMAC). The key lives in `AIRTABLE_TOKEN_ENCRYPTION_KEY` — never in the DB. Losing the key orphans stored tokens.
- **whoami validation on every connect** — invalid tokens are rejected before anything is written. Missing required scopes are surfaced to the frontend so the user can regenerate the token.
- **Decryption failures are logged and treated as "not connected"** — if the encryption key changes, the user is prompted to reconnect rather than the app crashing.
- **No secret is ever returned by the GET endpoint** — only email, scopes, and timestamps. The frontend has no way to read back the raw PAT.
- **Airtable PAT scopes are also visible to the user in the UI** — the connection pill shows a warning icon if required scopes are missing.

---

## Data model of imported documents

Each Airtable record produces one `Document`:

- `doc_type = 'airtable'`
- `title` — value of the user-chosen title field (or the record's primary field if none chosen).
- `content` — markdown body. First line is `_Source: Airtable — {base_name} / {table_name} — record \`{record_id}\`_`. Each selected content field renders as a `## Field Name` section. Lists, linked records, and attachments are serialized to readable bullet-point strings.
- `airtable_source_ref` — `{"base_id": "app...", "table_id": "tbl...", "record_id": "rec..."}`. Index: partial `idx_documents_airtable_record` on `airtable_source_ref->>'record_id'`.
- `processing_status` — follows the normal `pending → embedding → completed` lifecycle from `DocProcessingService`.

---

## Intentionally out of scope

- **Incremental / webhook-driven updates.** Re-imports are manual. Airtable webhooks for change-driven sync are out of scope for the POC.
- **Deleting records in Airtable does not delete imported documents.**
- **Attachments are linked by URL in the markdown, not downloaded.** The RAG pipeline sees the filename and URL but not file contents.
- **Multi-user auth.** The design uses `user_id='default'` and one connection row for the whole instance.
