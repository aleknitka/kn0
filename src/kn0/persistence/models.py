"""SQLAlchemy Core table definitions for kn0."""

from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    text,
)


metadata = MetaData()

documents = Table(
    "documents",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("filename", Text, nullable=False),
    Column("file_hash", String(64), unique=True, nullable=False),
    Column("file_size", Integer),
    Column("mime_type", Text),
    Column("page_count", Integer),
    Column("language", Text),
    Column(
        "status",
        String(20),
        nullable=False,
        server_default="pending",
    ),
    Column("source_reliability", Float, server_default=text("0.5")),
    Column("error_message", Text),
    Column("created_at", Text, nullable=False),
    Column("updated_at", Text, nullable=False),
)

entities = Table(
    "entities",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("canonical_name", Text, nullable=False),
    Column("entity_type", String(30), nullable=False),
    Column("aliases", Text, nullable=False, server_default="[]"),   # JSON array
    Column("attributes", Text, nullable=False, server_default="{}"),  # JSON object
    Column("mention_count", Integer, nullable=False, server_default=text("0")),
    Column("first_seen", Text, nullable=False),
    Column("last_updated", Text, nullable=False),
    Index("ix_entities_type", "entity_type"),
)

relationships = Table(
    "relationships",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("source_entity_id", String(36), ForeignKey("entities.id"), nullable=False),
    Column("target_entity_id", String(36), ForeignKey("entities.id"), nullable=False),
    Column("relationship_type", Text, nullable=False),
    Column("confidence_score", Float, nullable=False, server_default=text("0.0")),
    Column(
        "status",
        String(20),
        nullable=False,
        server_default="ACTIVE",
    ),
    Column("first_seen", Text, nullable=False),
    Column("last_confirmed", Text, nullable=False),
    Index("ix_relationships_source", "source_entity_id"),
    Index("ix_relationships_target", "target_entity_id"),
    Index(
        "ix_relationships_unique",
        "source_entity_id",
        "target_entity_id",
        "relationship_type",
        unique=True,
    ),
)

entity_mentions = Table(
    "entity_mentions",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("entity_id", String(36), ForeignKey("entities.id"), nullable=False),
    Column("document_id", String(36), ForeignKey("documents.id"), nullable=False),
    Column("page_number", Integer),
    Column("char_offset", Integer),
    Column("text_span", Text, nullable=False),
    Column("context_window", Text),
    Column("created_at", Text, nullable=False),
    Index("ix_entity_mentions_entity", "entity_id"),
    Index("ix_entity_mentions_document", "document_id"),
)

relationship_evidence = Table(
    "relationship_evidence",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("relationship_id", String(36), ForeignKey("relationships.id"), nullable=False),
    Column("document_id", String(36), ForeignKey("documents.id"), nullable=False),
    Column("page_number", Integer),
    Column("passage_text", Text, nullable=False),
    Column("context_window", Text),
    Column("extraction_method", Text, nullable=False),
    Column("individual_confidence", Float, nullable=False),
    Column(
        "validation_status",
        String(20),
        nullable=False,
        server_default="unreviewed",
    ),
    Column("created_at", Text, nullable=False),
    Index("ix_rel_evidence_relationship", "relationship_id"),
    Index("ix_rel_evidence_document", "document_id"),
)

events = Table(
    "events",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("title", Text, nullable=False),
    Column("event_type", String(50), nullable=False),
    Column("description", Text),
    Column("start_date", Text),           # ISO 8601 "YYYY-MM-DD"; NULL = undated
    Column("end_date", Text),             # NULL = point-in-time event
    Column("location_entity_id", String(36), ForeignKey("entities.id")),
    Column("attributes", Text, nullable=False, server_default="{}"),
    Column("created_at", Text, nullable=False),
    Column("updated_at", Text, nullable=False),
    Index("ix_events_type", "event_type"),
    Index("ix_events_start_date", "start_date"),
    Index("ix_events_location", "location_entity_id"),
)

event_participants = Table(
    "event_participants",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("event_id", String(36), ForeignKey("events.id"), nullable=False),
    Column("entity_id", String(36), ForeignKey("entities.id"), nullable=False),
    Column("role", Text),
    Column("created_at", Text, nullable=False),
    Index("ix_ep_event", "event_id"),
    Index("ix_ep_entity", "entity_id"),
    Index("ix_ep_unique", "event_id", "entity_id", "role", unique=True),
)

event_source_documents = Table(
    "event_source_documents",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("event_id", String(36), ForeignKey("events.id"), nullable=False),
    Column("document_id", String(36), ForeignKey("documents.id"), nullable=False),
    Column("passage_text", Text),
    Column("confidence", Float, nullable=False, server_default=text("0.5")),
    Column("created_at", Text, nullable=False),
    Index("ix_esd_event", "event_id"),
    Index("ix_esd_document", "document_id"),
    Index("ix_esd_unique", "event_id", "document_id", unique=True),
)
