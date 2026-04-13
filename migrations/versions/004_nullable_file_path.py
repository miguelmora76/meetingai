"""Make meetings.file_path nullable to support two-phase upload.

The upload endpoint creates the DB record before writing the file to disk,
so file_path starts as NULL and is updated once the file is saved.

Revision ID: 004
Create Date: 2026-04-13
"""

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("meetings", "file_path", existing_type=sa.String(1000), nullable=True)


def downgrade() -> None:
    op.alter_column("meetings", "file_path", existing_type=sa.String(1000), nullable=False)
