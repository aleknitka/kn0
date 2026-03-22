"""Initial database schema.

Revision ID: 001
Revises:
Create Date: 2026-03-21
"""

from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("filename", sa.Text, nullable=False),
        sa.Column("file_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("file_size", sa.Integer),
        sa.Column("mime_type", sa.Text),
        sa.Column("page_count", sa.Integer),
        sa.Column("language", sa.Text),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("source_reliability", sa.Float, server_default=sa.text("0.5")),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.Column("updated_at", sa.Text, nullable=False),
    )

    op.create_table(
        "entities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("canonical_name", sa.Text, nullable=False),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("aliases", sa.Text, nullable=False, server_default="[]"),
        sa.Column("attributes", sa.Text, nullable=False, server_default="{}"),
        sa.Column("mention_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("first_seen", sa.Text, nullable=False),
        sa.Column("last_updated", sa.Text, nullable=False),
    )
    op.create_index("ix_entities_type", "entities", ["entity_type"])

    op.create_table(
        "relationships",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_entity_id", sa.String(36), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("target_entity_id", sa.String(36), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("relationship_type", sa.Text, nullable=False),
        sa.Column("confidence_score", sa.Float, nullable=False, server_default=sa.text("0.0")),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("first_seen", sa.Text, nullable=False),
        sa.Column("last_confirmed", sa.Text, nullable=False),
    )
    op.create_index("ix_relationships_source", "relationships", ["source_entity_id"])
    op.create_index("ix_relationships_target", "relationships", ["target_entity_id"])
    op.create_index(
        "ix_relationships_unique",
        "relationships",
        ["source_entity_id", "target_entity_id", "relationship_type"],
        unique=True,
    )

    op.create_table(
        "entity_mentions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entity_id", sa.String(36), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("page_number", sa.Integer),
        sa.Column("char_offset", sa.Integer),
        sa.Column("text_span", sa.Text, nullable=False),
        sa.Column("context_window", sa.Text),
        sa.Column("created_at", sa.Text, nullable=False),
    )
    op.create_index("ix_entity_mentions_entity", "entity_mentions", ["entity_id"])
    op.create_index("ix_entity_mentions_document", "entity_mentions", ["document_id"])

    op.create_table(
        "relationship_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "relationship_id", sa.String(36), sa.ForeignKey("relationships.id"), nullable=False
        ),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("page_number", sa.Integer),
        sa.Column("passage_text", sa.Text, nullable=False),
        sa.Column("context_window", sa.Text),
        sa.Column("extraction_method", sa.Text, nullable=False),
        sa.Column("individual_confidence", sa.Float, nullable=False),
        sa.Column(
            "validation_status", sa.String(20), nullable=False, server_default="unreviewed"
        ),
        sa.Column("created_at", sa.Text, nullable=False),
    )
    op.create_index("ix_rel_evidence_relationship", "relationship_evidence", ["relationship_id"])
    op.create_index("ix_rel_evidence_document", "relationship_evidence", ["document_id"])


def downgrade() -> None:
    op.drop_table("relationship_evidence")
    op.drop_table("entity_mentions")
    op.drop_table("relationships")
    op.drop_table("entities")
    op.drop_table("documents")
