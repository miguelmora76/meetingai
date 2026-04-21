"""User-owned Airtable connection: PAT storage + import tracking.

Revision ID: 006
Create Date: 2026-04-21
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "airtable_connections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", sa.String(100), nullable=False, server_default="default", unique=True),
        sa.Column("airtable_user_id", sa.String(100)),
        sa.Column("airtable_email", sa.String(500)),
        sa.Column("access_token_encrypted", sa.Text, nullable=False),
        sa.Column("scopes", ARRAY(sa.String), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_table(
        "airtable_imports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("base_id", sa.String(100), nullable=False),
        sa.Column("base_name", sa.String(500)),
        sa.Column("table_id", sa.String(100), nullable=False),
        sa.Column("table_name", sa.String(500)),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("records_total", sa.Integer, server_default="0"),
        sa.Column("records_processed", sa.Integer, server_default="0"),
        sa.Column("documents_created", sa.Integer, server_default="0"),
        sa.Column("title_field", sa.String(500)),
        sa.Column("content_fields", ARRAY(sa.String), server_default="{}"),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_airtable_imports_status", "airtable_imports", ["status"])

    op.add_column("documents", sa.Column("airtable_source_ref", JSONB, nullable=True))
    op.create_index(
        "idx_documents_airtable_record",
        "documents",
        [sa.text("(airtable_source_ref->>'record_id')")],
        postgresql_where=sa.text("airtable_source_ref IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_documents_airtable_record", table_name="documents")
    op.drop_column("documents", "airtable_source_ref")
    op.drop_index("idx_airtable_imports_status", table_name="airtable_imports")
    op.drop_table("airtable_imports")
    op.drop_table("airtable_connections")
