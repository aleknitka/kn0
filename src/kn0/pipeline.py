"""End-to-end ingestion pipeline: parse → extract → persist."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import Connection

from kn0.config import settings
from kn0.extraction.base import ExtractedEntity, ExtractedRelationship
from kn0.extraction.confidence import compute_confidence, recalculate_from_evidence
from kn0.extraction.resolver import ResolutionOutcome, resolve_entity
from kn0.extraction.spacy_backend import SpacyBackend, get_default_backend
from kn0.ingestion.registry import ParserRegistry, default_registry
from kn0.persistence.store import DocumentStore, EntityStore, RelationshipStore

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    document_id: str
    filename: str
    was_duplicate: bool
    entities_created: int = 0
    entities_merged: int = 0
    relationships_created: int = 0
    relationships_updated: int = 0
    pages_processed: int = 0
    error: str | None = None


def ingest_document(
    file_path: Path,
    conn: Connection,
    *,
    registry: ParserRegistry | None = None,
    backend: SpacyBackend | None = None,
    source_reliability: float | None = None,
) -> IngestionResult:
    """
    Full pipeline: parse file → extract entities/relationships → persist to DB.

    Idempotent: re-ingesting the same file (by SHA-256 hash) is a no-op.
    """
    registry = registry or default_registry
    backend = backend or get_default_backend(settings.spacy_model)
    reliability = source_reliability if source_reliability is not None else settings.source_reliability_default

    doc_store = DocumentStore(conn)
    entity_store = EntityStore(conn)
    rel_store = RelationshipStore(conn)

    # 1. Hash check for idempotency
    file_hash = doc_store.hash_file(file_path)
    existing = doc_store.find_by_hash(file_hash)
    if existing:
        logger.info("Document already ingested: %s (id=%s)", file_path.name, existing["id"])
        return IngestionResult(
            document_id=existing["id"],
            filename=file_path.name,
            was_duplicate=True,
        )

    # 2. Register document record
    doc_id = doc_store.create(
        filename=file_path.name,
        file_hash=file_hash,
        file_size=file_path.stat().st_size,
        mime_type="",  # will be updated after parsing
    )

    try:
        doc_store.update_status(doc_id, "processing")

        # 3. Parse document
        parsed_doc, mime_type = registry.parse(file_path)
        doc_store.update_status(
            doc_id,
            "processing",
            page_count=parsed_doc.page_count,
            language=parsed_doc.language,
        )
        # Update mime_type directly
        from sqlalchemy import update
        from kn0.persistence.models import documents
        conn.execute(
            update(documents).where(documents.c.id == doc_id).values(mime_type=mime_type)
        )

        result = IngestionResult(
            document_id=doc_id,
            filename=file_path.name,
            was_duplicate=False,
            pages_processed=parsed_doc.page_count,
        )

        # 4. Extract and persist per page
        for page in parsed_doc.pages:
            if not page.text.strip():
                continue

            # Entity extraction
            extracted_entities = backend.extract_entities(page.text, page.page_number)
            entity_id_map: dict[str, str] = {}  # text → entity_id

            for ee in extracted_entities:
                entity_id = _persist_entity(
                    ee, doc_id, entity_store, result
                )
                if entity_id:
                    entity_id_map[ee.text] = entity_id

            # Relationship extraction (co-occurrence)
            extracted_rels = backend.extract_relationships(
                page.text, extracted_entities, page.page_number
            )
            for er in extracted_rels:
                _persist_relationship(
                    er, doc_id, entity_id_map, rel_store, reliability, result
                )

        doc_store.update_status(doc_id, "completed")
        logger.info(
            "Ingested %s: %d entities created, %d merged, %d relationships",
            file_path.name,
            result.entities_created,
            result.entities_merged,
            result.relationships_created + result.relationships_updated,
        )
        return result

    except Exception as exc:
        doc_store.update_status(doc_id, "failed", error_message=str(exc))
        logger.exception("Failed to ingest %s", file_path.name)
        result.error = str(exc)
        return result


def _persist_entity(
    ee: ExtractedEntity,
    doc_id: str,
    entity_store: EntityStore,
    result: IngestionResult,
) -> str | None:
    """Resolve extracted entity against DB, create or merge, add mention. Returns entity_id."""
    entity_type = ee.entity_type.value
    candidates = entity_store.find_candidates_by_type(entity_type)

    outcome, matched_id, score = resolve_entity(
        canonical_name=ee.text,
        entity_type=entity_type,
        candidates=candidates,
    )

    if outcome == ResolutionOutcome.MERGED and matched_id:
        # Add new name as alias if different from canonical
        existing = entity_store.get(matched_id)
        if existing and existing["canonical_name"].lower() != ee.text.lower():
            entity_store.add_alias(matched_id, ee.text)
        entity_id = matched_id
        result.entities_merged += 1

    elif outcome == ResolutionOutcome.UNDER_REVIEW and matched_id:
        # Keep as separate entity but flag (future: UNDER_REVIEW status field on entity)
        entity_id = entity_store.create(ee.text, entity_type)
        result.entities_created += 1

    else:  # CREATED
        entity_id = entity_store.create(ee.text, entity_type)
        result.entities_created += 1

    entity_store.add_mention(
        entity_id=entity_id,
        document_id=doc_id,
        text_span=ee.text,
        page_number=ee.page_number,
        char_offset=ee.start_char,
        context_window=ee.context_window,
    )
    return entity_id


def _persist_relationship(
    er: ExtractedRelationship,
    doc_id: str,
    entity_id_map: dict[str, str],
    rel_store: RelationshipStore,
    source_reliability: float,
    result: IngestionResult,
) -> None:
    """Persist extracted relationship with evidence, recalculating confidence."""
    src_id = entity_id_map.get(er.source_text)
    tgt_id = entity_id_map.get(er.target_text)
    if not src_id or not tgt_id or src_id == tgt_id:
        return

    existing_rel = rel_store.find(src_id, tgt_id, er.relationship_type)

    if existing_rel:
        rel_id = existing_rel["id"]
        result.relationships_updated += 1
    else:
        rel_id = rel_store.create(src_id, tgt_id, er.relationship_type)
        result.relationships_created += 1

    # Add evidence for this document
    rel_store.add_evidence(
        relationship_id=rel_id,
        document_id=doc_id,
        passage_text=er.passage,
        extraction_method=er.extraction_method,
        individual_confidence=er.confidence,
        page_number=er.page_number,
        context_window=er.context_window,
    )

    # Recalculate confidence from all evidence
    all_evidence = rel_store.get_evidence(rel_id)
    # Build source reliability map (simplified: same reliability for all docs)
    rel_map = {e["document_id"]: source_reliability for e in all_evidence}
    new_confidence = recalculate_from_evidence(all_evidence, rel_map)
    rel_store.update_confidence(rel_id, new_confidence)
