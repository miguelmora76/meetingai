"""
Airtable table → knowledge-base import.

Pulls every record from a user-selected Airtable table, turns each record into
a synthetic markdown document, and hands it off to DocProcessingService so the
existing chunk/embed/RAG pipeline can index it. Progress is tracked in the
airtable_imports table so the frontend can poll for status.

Design notes:
- pyairtable is synchronous; network calls are wrapped in asyncio.to_thread.
- If a record was previously imported (matched by base_id + record_id in the
  document's airtable_source_ref JSON column), the existing document is updated
  in place instead of duplicated.
- Content fields are rendered as markdown sections. Non-text cell values
  (lists, linked records, attachments) are serialized to readable strings.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.db.repository import DocumentRepository
from app.db.session import AsyncSessionLocal
from app.llm.client import LLMClient
from app.models.database import AirtableImport
from app.services.airtable_connection import AirtableConnectionService
from app.services.doc_processing import DocProcessingService

logger = logging.getLogger(__name__)

_TEXT_FIELD_TYPES = {
    "singleLineText",
    "multilineText",
    "richText",
    "email",
    "url",
    "phoneNumber",
    "formula",
    "rollup",
    "aiText",
}


class AirtableImportService:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings | None = None,
    ):
        self.db = db
        self.settings = settings or get_settings()

    async def create_import(
        self,
        *,
        base_id: str,
        base_name: str | None,
        table_id: str,
        table_name: str | None,
        title_field: str | None,
        content_fields: list[str],
    ) -> AirtableImport:
        row = AirtableImport(
            base_id=base_id,
            base_name=base_name,
            table_id=table_id,
            table_name=table_name,
            status="pending",
            title_field=title_field,
            content_fields=content_fields,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def get_import(self, import_id: uuid.UUID) -> AirtableImport | None:
        result = await self.db.execute(
            select(AirtableImport).where(AirtableImport.id == import_id)
        )
        return result.scalar_one_or_none()


async def run_airtable_import(import_id: uuid.UUID) -> None:
    """
    Background task: fetch the import row, pull all records from the configured
    table, write Documents, and enqueue embedding for each. Updates the import
    row's status/progress as it goes.
    """
    logger.info(f"[airtable-import {import_id}] starting")

    async with AsyncSessionLocal() as session:
        import_row = await _get_import_row(session, import_id)
        if not import_row:
            logger.error(f"[airtable-import {import_id}] row not found")
            return

        token_service = AirtableConnectionService(session)
        token = await token_service.get_decrypted_token()
        if not token:
            await _mark_failed(session, import_row, "Airtable is not connected")
            return

        await _update_status(session, import_row, "fetching")

    try:
        records = await asyncio.to_thread(
            _fetch_all_records,
            token,
            import_row.base_id,
            import_row.table_id,
        )
    except Exception as exc:
        logger.exception(f"[airtable-import {import_id}] fetch failed: {exc}")
        async with AsyncSessionLocal() as session:
            row = await _get_import_row(session, import_id)
            if row:
                await _mark_failed(session, row, f"Fetch failed: {exc}")
        return

    logger.info(f"[airtable-import {import_id}] fetched {len(records)} records")

    async with AsyncSessionLocal() as session:
        row = await _get_import_row(session, import_id)
        if not row:
            return
        row.records_total = len(records)
        row.status = "processing"
        row.updated_at = datetime.utcnow()
        await session.commit()
        title_field = row.title_field
        content_fields = list(row.content_fields or [])
        base_id = row.base_id
        base_name = row.base_name
        table_id = row.table_id
        table_name = row.table_name

    processed = 0
    created = 0
    doc_ids_to_embed: list[uuid.UUID] = []
    for record in records:
        try:
            doc_id, was_created = await _upsert_document_from_record(
                record=record,
                base_id=base_id,
                base_name=base_name,
                table_id=table_id,
                table_name=table_name,
                title_field=title_field,
                content_fields=content_fields,
            )
            if was_created:
                created += 1
            doc_ids_to_embed.append(doc_id)
        except Exception as exc:
            logger.warning(
                f"[airtable-import {import_id}] record {record.get('id')} failed: {exc}"
            )
        processed += 1
        # Lightweight per-batch progress updates
        if processed % 10 == 0 or processed == len(records):
            async with AsyncSessionLocal() as session:
                row = await _get_import_row(session, import_id)
                if row:
                    row.records_processed = processed
                    row.documents_created = created
                    row.updated_at = datetime.utcnow()
                    await session.commit()

    # Kick off embedding for each imported document. Run sequentially to keep
    # the embedding model memory footprint predictable for POC.
    for doc_id in doc_ids_to_embed:
        try:
            await _embed_document(doc_id)
        except Exception as exc:
            logger.warning(f"[airtable-import {import_id}] embed {doc_id} failed: {exc}")

    async with AsyncSessionLocal() as session:
        row = await _get_import_row(session, import_id)
        if row:
            row.status = "completed"
            row.records_processed = processed
            row.documents_created = created
            row.updated_at = datetime.utcnow()
            await session.commit()

    logger.info(
        f"[airtable-import {import_id}] done: {processed} records, {created} new documents"
    )


# ── Helpers ───────────────────────────────────────────────────────────────


async def _get_import_row(session: AsyncSession, import_id: uuid.UUID) -> AirtableImport | None:
    result = await session.execute(
        select(AirtableImport).where(AirtableImport.id == import_id)
    )
    return result.scalar_one_or_none()


async def _update_status(session: AsyncSession, row: AirtableImport, status: str) -> None:
    row.status = status
    row.updated_at = datetime.utcnow()
    await session.commit()


async def _mark_failed(session: AsyncSession, row: AirtableImport, message: str) -> None:
    row.status = "failed"
    row.error_message = message[:1000]
    row.updated_at = datetime.utcnow()
    await session.commit()


def _fetch_all_records(token: str, base_id: str, table_id: str) -> list[dict]:
    """Synchronous: paginate through every record via pyairtable."""
    from pyairtable import Api

    api = Api(token)
    table = api.table(base_id, table_id)
    return table.all()


async def _upsert_document_from_record(
    *,
    record: dict,
    base_id: str,
    base_name: str | None,
    table_id: str,
    table_name: str | None,
    title_field: str | None,
    content_fields: list[str],
) -> tuple[uuid.UUID, bool]:
    """Create or update a Document for a single Airtable record. Returns (doc_id, was_created)."""
    record_id = record["id"]
    fields: dict[str, Any] = record.get("fields", {}) or {}

    title = _extract_title(fields, title_field)
    body = _build_markdown_body(
        fields=fields,
        content_fields=content_fields,
        base_name=base_name,
        table_name=table_name,
        record_id=record_id,
    )

    source_ref = {
        "base_id": base_id,
        "table_id": table_id,
        "record_id": record_id,
    }

    async with AsyncSessionLocal() as session:
        repo = DocumentRepository(session)
        existing = await repo.find_document_by_airtable_record(base_id, record_id)
        if existing:
            existing.title = title
            existing.content = body
            existing.processing_status = "pending"
            existing.error_message = None
            existing.updated_at = datetime.utcnow()
            # Drop old chunks so re-embedding produces a clean set
            for chunk in existing.chunks:
                await session.delete(chunk)
            await session.commit()
            return existing.id, False

        doc = await repo.create_document(
            title=title,
            doc_type="airtable",
            content=body,
            airtable_source_ref=source_ref,
        )
        return doc.id, True


async def _embed_document(document_id: uuid.UUID) -> None:
    """Run the existing DocProcessingService against a document id."""
    async with AsyncSessionLocal() as session:
        repo = DocumentRepository(session)
        llm_client = LLMClient()
        service = DocProcessingService(doc_repo=repo, llm_client=llm_client)
        await service.process_document(document_id)


def _extract_title(fields: dict[str, Any], title_field: str | None) -> str:
    if title_field and title_field in fields:
        value = fields[title_field]
        if value:
            return str(value)[:500]

    # Fall back to the first non-empty string-looking field
    for k, v in fields.items():
        if isinstance(v, str) and v.strip():
            return v.strip()[:500]

    return "Untitled Airtable record"


def _build_markdown_body(
    *,
    fields: dict[str, Any],
    content_fields: list[str],
    base_name: str | None,
    table_name: str | None,
    record_id: str,
) -> str:
    """Render selected fields as markdown. Empty content_fields = include every field."""
    chosen = content_fields if content_fields else list(fields.keys())

    lines: list[str] = []
    location = " / ".join(x for x in [base_name, table_name] if x)
    if location:
        lines.append(f"_Source: Airtable — {location} — record `{record_id}`_")
        lines.append("")

    for name in chosen:
        if name not in fields:
            continue
        rendered = _render_value(fields[name])
        if not rendered.strip():
            continue
        lines.append(f"## {name}")
        lines.append(rendered)
        lines.append("")

    return "\n".join(lines).strip() or "(empty record)"


def _render_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                # Attachments: {url, filename}; linked records: {id}
                if "filename" in item:
                    parts.append(f"- {item.get('filename')} ({item.get('url', '')})")
                elif "name" in item:
                    parts.append(f"- {item['name']}")
                else:
                    parts.append(f"- {item.get('id', str(item))}")
            else:
                parts.append(f"- {item}")
        return "\n".join(parts)
    if isinstance(value, dict):
        if "name" in value:
            return str(value["name"])
        return ", ".join(f"{k}: {v}" for k, v in value.items())
    return str(value)
