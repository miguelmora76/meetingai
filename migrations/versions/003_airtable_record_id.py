"""Add airtable_record_id to incidents and airtable settings support.

Revision ID: 003
Create Date: 2026-04-02
"""

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "incidents",
        sa.Column("airtable_record_id", sa.String(100), nullable=True),
    )
    op.create_index(
        "idx_incidents_airtable_record_id",
        "incidents",
        ["airtable_record_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_incidents_airtable_record_id", table_name="incidents")
    op.drop_column("incidents", "airtable_record_id")
