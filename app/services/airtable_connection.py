"""
User-owned Airtable connection service.

Stores a user's Airtable personal access token (PAT), encrypted with Fernet,
and provides helpers to validate, retrieve, and delete it. The stored token
is used by the import worker and bases/tables listing endpoints — in single-
user POC mode there is exactly one connection, keyed by user_id='default'.

Design:
- Tokens are encrypted at rest with a symmetric Fernet key from settings.
  Losing the key orphans stored tokens (they must be re-entered by the user).
- Validation calls Airtable's /meta/whoami endpoint before persisting, so we
  never store an invalid token.
- Scope detection: whoami returns the token's scopes; we persist them so the
  frontend can warn if the user pasted a token without the scopes we need.
"""

import logging
from dataclasses import dataclass
from typing import Any

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.models.database import AirtableConnection

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default"
WHOAMI_URL = "https://api.airtable.com/v0/meta/whoami"
REQUIRED_SCOPES = {"data.records:read", "schema.bases:read"}


class AirtableTokenError(Exception):
    """Raised when the provided PAT fails validation against Airtable."""


@dataclass
class WhoAmI:
    airtable_user_id: str
    email: str | None
    scopes: list[str]


class AirtableConnectionService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None):
        self.db = db
        self.settings = settings or get_settings()
        self._fernet = _get_fernet(self.settings)

    # ── Public API ─────────────────────────────────────────────────────

    async def validate_token(self, token: str) -> WhoAmI:
        """Call Airtable whoami. Raises AirtableTokenError on failure."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(
                    WHOAMI_URL,
                    headers={"Authorization": f"Bearer {token}"},
                )
            except httpx.HTTPError as exc:
                raise AirtableTokenError(f"Network error contacting Airtable: {exc}") from exc

        if resp.status_code == 401:
            raise AirtableTokenError("Airtable rejected the token (401). Check that it is active.")
        if resp.status_code == 403:
            raise AirtableTokenError("Token is missing required scopes (403).")
        if resp.status_code >= 400:
            raise AirtableTokenError(f"Airtable returned {resp.status_code}: {resp.text[:200]}")

        data: dict[str, Any] = resp.json()
        return WhoAmI(
            airtable_user_id=data.get("id", ""),
            email=data.get("email"),
            scopes=data.get("scopes", []) or [],
        )

    async def save(self, token: str, whoami: WhoAmI) -> AirtableConnection:
        """Upsert the (single-user) connection row with the encrypted token."""
        encrypted = self._encrypt(token)

        existing = await self._get_row()
        if existing:
            existing.access_token_encrypted = encrypted
            existing.airtable_user_id = whoami.airtable_user_id
            existing.airtable_email = whoami.email
            existing.scopes = whoami.scopes
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        row = AirtableConnection(
            user_id=DEFAULT_USER_ID,
            airtable_user_id=whoami.airtable_user_id,
            airtable_email=whoami.email,
            access_token_encrypted=encrypted,
            scopes=whoami.scopes,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def get(self) -> AirtableConnection | None:
        return await self._get_row()

    async def get_decrypted_token(self) -> str | None:
        row = await self._get_row()
        if not row:
            return None
        try:
            return self._decrypt(row.access_token_encrypted)
        except InvalidToken:
            logger.error(
                "Failed to decrypt stored Airtable token — likely AIRTABLE_TOKEN_ENCRYPTION_KEY changed. "
                "User must reconnect."
            )
            return None

    async def delete(self) -> bool:
        result = await self.db.execute(
            delete(AirtableConnection).where(AirtableConnection.user_id == DEFAULT_USER_ID)
        )
        await self.db.commit()
        return result.rowcount > 0

    # ── Internal ───────────────────────────────────────────────────────

    async def _get_row(self) -> AirtableConnection | None:
        result = await self.db.execute(
            select(AirtableConnection).where(AirtableConnection.user_id == DEFAULT_USER_ID)
        )
        return result.scalar_one_or_none()

    def _encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def _decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")


def _get_fernet(settings: Settings) -> Fernet:
    key = settings.airtable_token_encryption_key
    if not key:
        raise RuntimeError(
            "AIRTABLE_TOKEN_ENCRYPTION_KEY is not set. Generate one with: "
            'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    try:
        return Fernet(key.encode("ascii") if isinstance(key, str) else key)
    except Exception as exc:
        raise RuntimeError(
            f"AIRTABLE_TOKEN_ENCRYPTION_KEY is not a valid Fernet key: {exc}"
        ) from exc
