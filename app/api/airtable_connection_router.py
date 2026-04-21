"""
Airtable user-connection endpoints.

The user pastes their personal access token (PAT) in the frontend; the app
validates it against Airtable's whoami endpoint, encrypts it at rest, and
uses it for subsequent bases/tables/import operations.

Endpoints:
    POST   /airtable/connect      — validate + store a PAT
    GET    /airtable/connection   — current connection metadata
    DELETE /airtable/connection   — remove the stored connection
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.schemas import AirtableConnectionResponse, AirtableConnectRequest
from app.services.airtable_connection import (
    REQUIRED_SCOPES,
    AirtableConnectionService,
    AirtableTokenError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/airtable", tags=["airtable-connection"])


@router.post("/connect", response_model=AirtableConnectionResponse)
async def connect_airtable(
    payload: AirtableConnectRequest,
    db: AsyncSession = Depends(get_db),
):
    """Validate a PAT with Airtable and store it encrypted."""
    service = AirtableConnectionService(db)
    try:
        whoami = await service.validate_token(payload.token)
    except AirtableTokenError as exc:
        raise HTTPException(400, str(exc))
    except RuntimeError as exc:
        # Encryption key misconfigured
        raise HTTPException(500, str(exc))

    row = await service.save(payload.token, whoami)
    logger.info(f"[airtable] PAT stored for {whoami.email or whoami.airtable_user_id}")

    missing = sorted(REQUIRED_SCOPES - set(whoami.scopes))
    return AirtableConnectionResponse(
        connected=True,
        airtable_email=row.airtable_email,
        scopes=row.scopes or [],
        missing_required_scopes=missing,
        connected_at=row.updated_at or row.created_at,
    )


@router.get("/connection", response_model=AirtableConnectionResponse)
async def get_connection(db: AsyncSession = Depends(get_db)):
    service = AirtableConnectionService(db)
    row = await service.get()
    if not row:
        return AirtableConnectionResponse(connected=False)

    missing = sorted(REQUIRED_SCOPES - set(row.scopes or []))
    return AirtableConnectionResponse(
        connected=True,
        airtable_email=row.airtable_email,
        scopes=row.scopes or [],
        missing_required_scopes=missing,
        connected_at=row.updated_at or row.created_at,
    )


@router.delete("/connection", status_code=204)
async def delete_connection(db: AsyncSession = Depends(get_db)):
    service = AirtableConnectionService(db)
    await service.delete()
    return None
