"""Add airtable_record_id to meetings and documents tables.

Revision ID: 005
Create Date: 2026-04-14
"""

import sqlalchemy as sa
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("meetings", sa.Column("airtable_record_id", sa.String(100), nullable=True))
    op.add_column("documents", sa.Column("airtable_record_id", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("meetings", "airtable_record_id")
    op.drop_column("documents", "airtable_record_id")
