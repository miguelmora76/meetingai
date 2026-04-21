"""
Centralized application configuration.

All values are sourced from environment variables with sensible defaults.
Use get_settings() to access the singleton instance.
"""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ── Database ──────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://meetingai:meetingai@localhost:5432/meetingai"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_pre_ping: bool = True

    # ── LLM ───────────────────────────────────────────────────────────────
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    summarization_model: str = "claude-sonnet-4-6"
    extraction_model: str = "claude-haiku-4-5-20251001"
    embedding_model: str = "all-MiniLM-L6-v2"

    # ── Whisper ───────────────────────────────────────────────────────────
    whisper_mode: str = "local"  # "api" (OpenAI API) or "local"
    whisper_model: str = "base"  # for local mode: tiny, base, small, medium, large
    openai_api_key: str = ""  # needed for Whisper API mode

    # ── Airtable ──────────────────────────────────────────────────────────
    airtable_enabled: bool = False
    airtable_api_key: str = ""
    airtable_base_id: str = ""
    airtable_table_name: str = "Incidents"       # incidents table (kept for backwards compat)
    airtable_meetings_table_name: str = "Meetings"
    airtable_docs_table_name: str = "Documents"
    airtable_webhook_secret: str = ""            # Bearer token for POST /airtable/webhook
    app_base_url: str = "http://localhost:8000"

    # Fernet key for encrypting user-provided Airtable PATs at rest.
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # Must be stable across restarts — losing it orphans all stored tokens.
    airtable_token_encryption_key: str = ""

    # ── Slack ─────────────────────────────────────────────────────────────
    slack_enabled: bool = False
    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    slack_default_channel: str = ""

    # ── Security ──────────────────────────────────────────────────────────
    # Bearer token required for POST /admin/reset.
    # Must be set to a non-empty value — validated at startup.
    admin_token: str = ""
    # Comma-separated list of CORS-allowed origins (parsed in main.py).
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"

    # ── Storage ───────────────────────────────────────────────────────────
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 500

    # ── RAG ───────────────────────────────────────────────────────────────
    chunk_size: int = 1500
    chunk_overlap: int = 200
    retrieval_top_k: int = 5

    # ── Background tasks ─────────────────────────────────────────────────
    processing_timeout_seconds: int = 1800

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def validate_required_keys(self) -> "Settings":
        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic. "
                "Set it in your .env file or environment."
            )
        if self.whisper_mode == "api" and not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is required when WHISPER_MODE=api. "
                "Set it in your .env file or environment."
            )
        if not self.admin_token:
            raise ValueError(
                "ADMIN_TOKEN must be set to a non-empty value. "
                "The /admin/reset endpoint requires it for protection."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
