"""Data access layer: DocumentStore, EntityStore, RelationshipStore."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.engine import Connection

from kn0.persistence.models import (
    documents,
    entities,
    entity_mentions,
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
