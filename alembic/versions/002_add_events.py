"""Add events, event_participants, and event_source_documents tables.

Revision ID: 002
Revises: 001
Create Date: 2026-03-21
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("start_date", sa.Text),
        sa.Column("end_date", sa.Text),
        sa.Column(
            "location_entity_id",
            sa.String(36),
            sa.ForeignKey("entities.id"),
        ),
        sa.Column("attributes", sa.Text, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.Column("updated_at", sa.Text, nullable=False),
    )
    op.create_index("ix_events_type", "events", ["event_type"])
    op.create_index("ix_events_start_date", "events", ["start_date"])
    op.create_index("ix_events_location", "events", ["location_entity_id"])

    op.create_table(
        "event_participants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(36), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("entity_id", sa.String(36), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("role", sa.Text),
        sa.Column("created_at", sa.Text, nullable=False),
    )
    op.create_index("ix_ep_event", "event_participants", ["event_id"])
    op.create_index("ix_ep_entity", "event_participants", ["entity_id"])
    op.create_index(
        "ix_ep_unique",
        "event_participants",
        ["event_id", "entity_id", "role"],
        unique=True,
    )

    op.create_table(
        "event_source_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(36), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("passage_text", sa.Text),
        sa.Column("confidence", sa.Float, nullable=False, server_default=sa.text("0.5")),
        sa.Column("created_at", sa.Text, nullable=False),
    )
    op.create_index("ix_esd_event", "event_source_documents", ["event_id"])
    op.create_index("ix_esd_document", "event_source_documents", ["document_id"])
    op.create_index(
        "ix_esd_unique",
        "event_source_documents",
        ["event_id", "document_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("event_source_documents")
    op.drop_table("event_participants")
    op.drop_table("events")
