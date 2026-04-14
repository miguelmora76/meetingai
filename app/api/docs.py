"""
Docs API — upload and manage architecture / knowledge-base documents.
"""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.db.repository import DocumentRepository
from app.db.session import get_db
from app.limiter import limiter
from app.models.schemas import (
    AirtableSyncResponse,
    DocumentDetail,
    DocumentListItem,
    DocumentListResponse,
    DocumentUploadResponse,
)
from app.services.airtable_sync import AirtableSyncService
from app.workers.tasks import process_document_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge-base", tags=["knowledge-base"])

ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".log", ".yaml", ".yml", ".json", ".csv", ".rst", ".py",
}


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    title: str = "",
    doc_type: str = "architecture",
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Upload a knowledge-base document and start embedding."""
    suffix = Path(file.filename).suffix.lower() if file.filename else ""
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported file type '{suffix}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(413, f"File too large. Maximum: {settings.max_upload_size_mb} MB")

    upload_dir = Path(settings.upload_dir) / "docs"
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = uuid.uuid4()
    file_path = upload_dir / f"{file_id}{suffix}"
    with open(file_path, "wb") as f:
        f.write(content)

    repo = DocumentRepository(db)
    doc = await repo.create_document(
        title=title,
        doc_type=doc_type,
        file_path=str(file_path),
        file_name=file.filename,
        file_size_bytes=len(content),
    )

    background_tasks.add_task(process_document_task, doc.id)

    logger.info(f"Document uploaded: {doc.id} ({file.filename})")

    return DocumentUploadResponse(
        id=doc.id,
        title=doc.title,
        processing_status=doc.processing_status,
        file_name=doc.file_name,
        created_at=doc.created_at,
    )


@router.post("/{document_id}/sync", response_model=AirtableSyncResponse)
async def sync_document_to_airtable(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Manually push (or re-push) a document to Airtable."""
    if not settings.airtable_enabled:
        raise HTTPException(503, "Airtable integration is not enabled")

    repo = DocumentRepository(db)
    doc = await repo.get_document(document_id)

    if not doc:
        raise HTTPException(404, "Document not found")

    airtable = AirtableSyncService(settings)
    record_id = await airtable.push_document(
        document_id=document_id,
        title=doc.title,
        doc_type=doc.doc_type or "architecture",
        file_name=doc.file_name,
        processing_status=doc.processing_status,
        existing_record_id=doc.airtable_record_id,
    )

    if record_id:
        await repo.update_document_airtable_id(document_id, record_id)

    return AirtableSyncResponse(airtable_record_id=record_id, synced=record_id is not None)


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get document details."""
    repo = DocumentRepository(db)
    doc = await repo.get_document(document_id)

    if not doc:
        raise HTTPException(404, "Document not found")

    return DocumentDetail.model_validate(doc)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List all knowledge-base documents."""
    if page < 1:
        page = 1
    page_size = min(max(page_size, 1), 50)

    repo = DocumentRepository(db)
    docs, total = await repo.list_documents(page=page, page_size=page_size)

    return DocumentListResponse(
        items=[DocumentListItem.model_validate(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )
