"""Incidents, postmortems, timeline events, incident action items, incident chunks,
documents, and doc chunks.

Revision ID: 002
Create Date: 2026-03-28
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID, ARRAY

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Incidents
    op.create_table(
        "incidents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="sev3"),
        sa.Column("status", sa.String(50), nullable=False, server_default="open"),
        sa.Column("services_affected", ARRAY(sa.String), server_default="{}"),
        sa.Column("description", sa.Text),
        sa.Column("raw_text", sa.Text),
        sa.Column("file_path", sa.String(1000)),
        sa.Column("file_name", sa.String(500)),
        sa.Column("processing_status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text),
        sa.Column("occurred_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_incidents_processing_status", "incidents", ["processing_status"])
    op.create_index("idx_incidents_severity", "incidents", ["severity"])
    op.create_index("idx_incidents_status", "incidents", ["status"])

    # Incident postmortems
    op.create_table(
        "incident_postmortems",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("incident_id", UUID(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("executive_summary", sa.Text),
        sa.Column("root_cause_analysis", sa.Text),
        sa.Column("model_used", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_postmortems_incident", "incident_postmortems", ["incident_id"])

    # Incident timeline events
    op.create_table(
        "incident_timeline_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("incident_id", UUID(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_index", sa.Integer, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True)),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("event_type", sa.String(50), server_default="event"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_timeline_incident", "incident_timeline_events", ["incident_id", "event_index"])

    # Incident action items
    op.create_table(
        "incident_action_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("incident_id", UUID(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("assignee", sa.String(200)),
        sa.Column("due_date", sa.DateTime),
        sa.Column("priority", sa.String(20), server_default="medium"),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("category", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_incident_action_items_incident", "incident_action_items", ["incident_id"])

    # Incident embedding chunks
    op.create_table(
        "incident_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("incident_id", UUID(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("chunk_text", sa.Text, nullable=False),
        sa.Column("start_char", sa.Integer),
        sa.Column("end_char", sa.Integer),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_incident_chunks_incident", "incident_chunks", ["incident_id"])

    # Architecture / knowledge base documents
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("doc_type", sa.String(100), server_default="architecture"),
        sa.Column("file_path", sa.String(1000)),
        sa.Column("file_name", sa.String(500)),
        sa.Column("file_size_bytes", sa.BigInteger),
        sa.Column("content", sa.Text),
        sa.Column("processing_status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_documents_processing_status", "documents", ["processing_status"])
    op.create_index("idx_documents_doc_type", "documents", ["doc_type"])

    # Document embedding chunks
    op.create_table(
        "doc_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("chunk_text", sa.Text, nullable=False),
        sa.Column("start_char", sa.Integer),
        sa.Column("end_char", sa.Integer),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_doc_chunks_document", "doc_chunks", ["document_id"])


def downgrade() -> None:
    op.drop_table("doc_chunks")
    op.drop_table("documents")
    op.drop_table("incident_chunks")
    op.drop_table("incident_action_items")
    op.drop_table("incident_timeline_events")
    op.drop_table("incident_postmortems")
    op.drop_table("incidents")
