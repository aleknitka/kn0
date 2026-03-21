"""Data access layer: DocumentStore, EntityStore, RelationshipStore, EventStore."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, text, update
from sqlalchemy.engine import Connection

from kn0.persistence.models import (
    documents,
    entities,
    entity_mentions,
    event_participants,
    event_source_documents,
    events,
    relationship_evidence,
    relationships,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# DocumentStore
# ---------------------------------------------------------------------------


class DocumentStore:
    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def hash_file(self, file_path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def find_by_hash(self, file_hash: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            select(documents).where(documents.c.file_hash == file_hash)
        ).mappings().first()
        return dict(row) if row else None

    def create(
        self,
        filename: str,
        file_hash: str,
        file_size: int,
        mime_type: str,
    ) -> str:
        doc_id = _new_id()
        now = _now()
        self._conn.execute(
            documents.insert().values(
                id=doc_id,
                filename=filename,
                file_hash=file_hash,
                file_size=file_size,
                mime_type=mime_type,
                status="pending",
                created_at=now,
                updated_at=now,
            )
        )
        return doc_id

    def update_status(
        self,
        doc_id: str,
        status: str,
        *,
        page_count: int | None = None,
        language: str | None = None,
        error_message: str | None = None,
    ) -> None:
        values: dict[str, Any] = {"status": status, "updated_at": _now()}
        if page_count is not None:
            values["page_count"] = page_count
        if language is not None:
            values["language"] = language
        if error_message is not None:
            values["error_message"] = error_message
        self._conn.execute(update(documents).where(documents.c.id == doc_id).values(**values))

    def get(self, doc_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            select(documents).where(documents.c.id == doc_id)
        ).mappings().first()
        return dict(row) if row else None

    def list_all(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(select(documents)).mappings().all()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# EntityStore
# ---------------------------------------------------------------------------


class EntityStore:
    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def find_by_name_and_type(self, canonical_name: str, entity_type: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            select(entities).where(
                entities.c.canonical_name == canonical_name,
                entities.c.entity_type == entity_type,
            )
        ).mappings().first()
        return dict(row) if row else None

    def find_candidates_by_type(self, entity_type: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            select(entities).where(entities.c.entity_type == entity_type)
        ).mappings().all()
        return [dict(r) for r in rows]

    def create(
        self,
        canonical_name: str,
        entity_type: str,
        aliases: list[str] | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> str:
        entity_id = _new_id()
        now = _now()
        self._conn.execute(
            entities.insert().values(
                id=entity_id,
                canonical_name=canonical_name,
                entity_type=entity_type,
                aliases=json.dumps(aliases or []),
                attributes=json.dumps(attributes or {}),
                mention_count=0,
                first_seen=now,
                last_updated=now,
            )
        )
        return entity_id

    def add_alias(self, entity_id: str, alias: str) -> None:
        row = self._conn.execute(
            select(entities.c.aliases).where(entities.c.id == entity_id)
        ).scalar()
        current: list[str] = json.loads(row or "[]")
        if alias not in current:
            current.append(alias)
            self._conn.execute(
                update(entities)
                .where(entities.c.id == entity_id)
                .values(aliases=json.dumps(current), last_updated=_now())
            )

    def increment_mentions(self, entity_id: str) -> None:
        self._conn.execute(
            text(
                "UPDATE entities SET mention_count = mention_count + 1, last_updated = :now "
                "WHERE id = :id"
            ),
            {"now": _now(), "id": entity_id},
        )

    def add_mention(
        self,
        entity_id: str,
        document_id: str,
        text_span: str,
        page_number: int | None = None,
        char_offset: int | None = None,
        context_window: str | None = None,
    ) -> str:
        mention_id = _new_id()
        self._conn.execute(
            entity_mentions.insert().values(
                id=mention_id,
                entity_id=entity_id,
                document_id=document_id,
                page_number=page_number,
                char_offset=char_offset,
                text_span=text_span,
                context_window=context_window,
                created_at=_now(),
            )
        )
        self.increment_mentions(entity_id)
        return mention_id

    def get(self, entity_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            select(entities).where(entities.c.id == entity_id)
        ).mappings().first()
        return dict(row) if row else None

    def list_all(
        self,
        entity_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        q = select(entities)
        if entity_type:
            q = q.where(entities.c.entity_type == entity_type)
        q = q.limit(limit).offset(offset)
        rows = self._conn.execute(q).mappings().all()
        return [dict(r) for r in rows]

    def search_fts(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            text(
                "SELECT e.* FROM entities e "
                "JOIN entities_fts fts ON e.id = fts.entity_id "
                "WHERE entities_fts MATCH :query LIMIT :limit"
            ),
            {"query": query, "limit": limit},
        ).mappings().all()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# RelationshipStore
# ---------------------------------------------------------------------------


class RelationshipStore:
    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def find(
        self, source_entity_id: str, target_entity_id: str, relationship_type: str
    ) -> dict[str, Any] | None:
        row = self._conn.execute(
            select(relationships).where(
                relationships.c.source_entity_id == source_entity_id,
                relationships.c.target_entity_id == target_entity_id,
                relationships.c.relationship_type == relationship_type,
            )
        ).mappings().first()
        return dict(row) if row else None

    def create(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        confidence_score: float = 0.0,
    ) -> str:
        rel_id = _new_id()
        now = _now()
        self._conn.execute(
            relationships.insert().values(
                id=rel_id,
                source_entity_id=source_entity_id,
                target_entity_id=target_entity_id,
                relationship_type=relationship_type,
                confidence_score=confidence_score,
                status="ACTIVE",
                first_seen=now,
                last_confirmed=now,
            )
        )
        return rel_id

    def update_confidence(self, rel_id: str, confidence_score: float) -> None:
        self._conn.execute(
            update(relationships)
            .where(relationships.c.id == rel_id)
            .values(confidence_score=confidence_score, last_confirmed=_now())
        )

    def add_evidence(
        self,
        relationship_id: str,
        document_id: str,
        passage_text: str,
        extraction_method: str,
        individual_confidence: float,
        page_number: int | None = None,
        context_window: str | None = None,
    ) -> str:
        ev_id = _new_id()
        self._conn.execute(
            relationship_evidence.insert().values(
                id=ev_id,
                relationship_id=relationship_id,
                document_id=document_id,
                page_number=page_number,
                passage_text=passage_text,
                context_window=context_window,
                extraction_method=extraction_method,
                individual_confidence=individual_confidence,
                validation_status="unreviewed",
                created_at=_now(),
            )
        )
        return ev_id

    def get_evidence(self, relationship_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            select(relationship_evidence).where(
                relationship_evidence.c.relationship_id == relationship_id
            )
        ).mappings().all()
        return [dict(r) for r in rows]

    def list_all(
        self,
        relationship_type: str | None = None,
        min_confidence: float | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        q = select(relationships)
        if relationship_type:
            q = q.where(relationships.c.relationship_type == relationship_type)
        if min_confidence is not None:
            q = q.where(relationships.c.confidence_score >= min_confidence)
        q = q.limit(limit).offset(offset)
        rows = self._conn.execute(q).mappings().all()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# EventStore
# ---------------------------------------------------------------------------


class EventStore:
    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def create(
        self,
        title: str,
        event_type: str,
        *,
        description: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        location_entity_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> str:
        """Insert a new event row and return its UUID."""
        event_id = _new_id()
        now = _now()
        self._conn.execute(
            events.insert().values(
                id=event_id,
                title=title,
                event_type=event_type,
                description=description,
                start_date=start_date,
                end_date=end_date,
                location_entity_id=location_entity_id,
                attributes=json.dumps(attributes or {}),
                created_at=now,
                updated_at=now,
            )
        )
        return event_id

    def get(self, event_id: str) -> dict[str, Any] | None:
        """Fetch a single event row by ID, with parsed attributes."""
        row = self._conn.execute(
            select(events).where(events.c.id == event_id)
        ).mappings().first()
        if row is None:
            return None
        result = dict(row)
        result["attributes"] = json.loads(result.get("attributes") or "{}")
        return result

    def update(
        self,
        event_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Partial update of event fields; always refreshes updated_at."""
        values: dict[str, Any] = {"updated_at": _now()}
        if title is not None:
            values["title"] = title
        if description is not None:
            values["description"] = description
        if start_date is not None:
            values["start_date"] = start_date
        if end_date is not None:
            values["end_date"] = end_date
        if attributes is not None:
            values["attributes"] = json.dumps(attributes)
        self._conn.execute(update(events).where(events.c.id == event_id).values(**values))

    def add_participant(
        self,
        event_id: str,
        entity_id: str,
        role: str | None = None,
    ) -> str:
        """Link an entity to an event with an optional role; return participant row ID."""
        participant_id = _new_id()
        self._conn.execute(
            event_participants.insert().values(
                id=participant_id,
                event_id=event_id,
                entity_id=entity_id,
                role=role,
                created_at=_now(),
            )
        )
        return participant_id

    def remove_participant(
        self,
        event_id: str,
        entity_id: str,
        role: str | None = None,
    ) -> None:
        """Remove a participant link, optionally filtered by role."""
        q = event_participants.delete().where(
            event_participants.c.event_id == event_id,
            event_participants.c.entity_id == entity_id,
        )
        if role is not None:
            q = q.where(event_participants.c.role == role)
        self._conn.execute(q)

    def get_participants(self, event_id: str) -> list[dict[str, Any]]:
        """Return participant rows joined with entity canonical_name and type."""
        rows = self._conn.execute(
            select(
                event_participants.c.entity_id,
                event_participants.c.role,
                event_participants.c.created_at,
                entities.c.canonical_name,
                entities.c.entity_type,
            )
            .join(entities, event_participants.c.entity_id == entities.c.id)
            .where(event_participants.c.event_id == event_id)
        ).mappings().all()
        return [dict(r) for r in rows]

    def add_source_document(
        self,
        event_id: str,
        document_id: str,
        *,
        passage_text: str | None = None,
        confidence: float = 0.5,
    ) -> str:
        """Link a source document to an event; return source row ID."""
        source_id = _new_id()
        self._conn.execute(
            event_source_documents.insert().values(
                id=source_id,
                event_id=event_id,
                document_id=document_id,
                passage_text=passage_text,
                confidence=confidence,
                created_at=_now(),
            )
        )
        return source_id

    def get_source_documents(self, event_id: str) -> list[dict[str, Any]]:
        """Return source document rows for an event."""
        rows = self._conn.execute(
            select(event_source_documents).where(
                event_source_documents.c.event_id == event_id
            )
        ).mappings().all()
        return [dict(r) for r in rows]

    def list_all(
        self,
        event_type: str | None = None,
        start_date_gte: str | None = None,
        start_date_lte: str | None = None,
        entity_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List events with optional filters."""
        q = select(events)
        if event_type:
            q = q.where(events.c.event_type == event_type)
        if start_date_gte:
            q = q.where(events.c.start_date >= start_date_gte)
        if start_date_lte:
            q = q.where(events.c.start_date <= start_date_lte)
        if entity_id:
            subq = select(event_participants.c.event_id).where(
                event_participants.c.entity_id == entity_id
            )
            q = q.where(events.c.id.in_(subq))
        q = q.limit(limit).offset(offset)
        rows = self._conn.execute(q).mappings().all()
        result = []
        for row in rows:
            r = dict(row)
            r["attributes"] = json.loads(r.get("attributes") or "{}")
            result.append(r)
        return result

    def get_timeline(
        self,
        entity_id: str | None = None,
        event_type: str | None = None,
        start_date_gte: str | None = None,
        start_date_lte: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """
        Return EventSummary-shaped rows ordered chronologically.
        Undated events (start_date IS NULL) are sorted last.
        """
        participant_count_subq = (
            select(func.count())
            .where(event_participants.c.event_id == events.c.id)
            .correlate(events)
            .scalar_subquery()
            .label("participant_count")
        )
        q = select(
            events.c.id,
            events.c.title,
            events.c.event_type,
            events.c.start_date,
            events.c.end_date,
            participant_count_subq,
        )
        if event_type:
            q = q.where(events.c.event_type == event_type)
        if start_date_gte:
            q = q.where(events.c.start_date >= start_date_gte)
        if start_date_lte:
            q = q.where(events.c.start_date <= start_date_lte)
        if entity_id:
            subq = select(event_participants.c.event_id).where(
                event_participants.c.entity_id == entity_id
            )
            q = q.where(events.c.id.in_(subq))
        # NULLs last: dated events first, then undated
        q = q.order_by(
            events.c.start_date.is_(None),
            events.c.start_date.asc(),
        ).limit(limit)
        rows = self._conn.execute(q).mappings().all()
        return [dict(r) for r in rows]

    def delete(self, event_id: str) -> None:
        """Hard-delete an event and its participant/source links."""
        self._conn.execute(
            event_source_documents.delete().where(
                event_source_documents.c.event_id == event_id
            )
        )
        self._conn.execute(
            event_participants.delete().where(
                event_participants.c.event_id == event_id
            )
        )
        self._conn.execute(events.delete().where(events.c.id == event_id))
