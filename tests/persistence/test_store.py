"""Tests for persistence layer (DocumentStore, EntityStore, RelationshipStore)."""

from __future__ import annotations

import pytest

from kn0.persistence.store import DocumentStore, EntityStore, RelationshipStore


class TestDocumentStore:
    def test_create_and_get(self, doc_store: DocumentStore, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        file_hash = doc_store.hash_file(f)
        doc_id = doc_store.create("test.txt", file_hash, 5, "text/plain")
        row = doc_store.get(doc_id)
        assert row is not None
        assert row["filename"] == "test.txt"
        assert row["status"] == "pending"

    def test_find_by_hash(self, doc_store: DocumentStore, tmp_path):
        f = tmp_path / "dup.txt"
        f.write_text("duplicate")
        file_hash = doc_store.hash_file(f)
        doc_id = doc_store.create("dup.txt", file_hash, 9, "text/plain")
        found = doc_store.find_by_hash(file_hash)
        assert found is not None
        assert found["id"] == doc_id

    def test_find_by_hash_missing(self, doc_store: DocumentStore):
        assert doc_store.find_by_hash("nonexistent_hash") is None

    def test_update_status(self, doc_store: DocumentStore, tmp_path):
        f = tmp_path / "s.txt"
        f.write_text("x")
        doc_id = doc_store.create("s.txt", doc_store.hash_file(f), 1, "text/plain")
        doc_store.update_status(doc_id, "completed", page_count=3, language="en")
        row = doc_store.get(doc_id)
        assert row["status"] == "completed"
        assert row["page_count"] == 3
        assert row["language"] == "en"

    def test_list_all(self, doc_store: DocumentStore, tmp_path):
        for i in range(3):
            f = tmp_path / f"f{i}.txt"
            f.write_text(f"content{i}")
            doc_store.create(f"f{i}.txt", doc_store.hash_file(f), i, "text/plain")
        rows = doc_store.list_all()
        assert len(rows) == 3


class TestEntityStore:
    def test_create_and_get(self, entity_store: EntityStore):
        eid = entity_store.create("Apple Inc.", "ORGANIZATION")
        row = entity_store.get(eid)
        assert row is not None
        assert row["canonical_name"] == "Apple Inc."
        assert row["entity_type"] == "ORGANIZATION"
        assert row["mention_count"] == 0

    def test_add_alias(self, entity_store: EntityStore):
        import json
        eid = entity_store.create("United States", "LOCATION")
        entity_store.add_alias(eid, "US")
        entity_store.add_alias(eid, "USA")
        row = entity_store.get(eid)
        aliases = json.loads(row["aliases"])
        assert "US" in aliases
        assert "USA" in aliases

    def test_add_alias_no_duplicate(self, entity_store: EntityStore):
        import json
        eid = entity_store.create("Entity", "CONCEPT")
        entity_store.add_alias(eid, "E")
        entity_store.add_alias(eid, "E")  # duplicate
        row = entity_store.get(eid)
        aliases = json.loads(row["aliases"])
        assert aliases.count("E") == 1

    def test_add_mention_increments_count(self, entity_store: EntityStore, doc_store: DocumentStore, tmp_path):
        f = tmp_path / "m.txt"
        f.write_text("x")
        doc_id = doc_store.create("m.txt", doc_store.hash_file(f), 1, "text/plain")
        eid = entity_store.create("Tim Cook", "PERSON")
        entity_store.add_mention(eid, doc_id, "Tim Cook", page_number=1)
        entity_store.add_mention(eid, doc_id, "Tim Cook", page_number=2)
        row = entity_store.get(eid)
        assert row["mention_count"] == 2

    def test_list_all_with_type_filter(self, entity_store: EntityStore):
        entity_store.create("Person A", "PERSON")
        entity_store.create("Org B", "ORGANIZATION")
        persons = entity_store.list_all(entity_type="PERSON")
        assert len(persons) == 1
        assert persons[0]["canonical_name"] == "Person A"

    def test_find_by_name_and_type(self, entity_store: EntityStore):
        entity_store.create("Tesla", "ORGANIZATION")
        row = entity_store.find_by_name_and_type("Tesla", "ORGANIZATION")
        assert row is not None
        assert row["canonical_name"] == "Tesla"

    def test_find_by_name_and_type_miss(self, entity_store: EntityStore):
        assert entity_store.find_by_name_and_type("Nonexistent", "PERSON") is None


class TestRelationshipStore:
    def test_create_and_find(self, rel_store: RelationshipStore, entity_store: EntityStore):
        src = entity_store.create("Alice", "PERSON")
        tgt = entity_store.create("Acme", "ORGANIZATION")
        rel_id = rel_store.create(src, tgt, "WORKS_FOR", confidence_score=0.6)
        found = rel_store.find(src, tgt, "WORKS_FOR")
        assert found is not None
        assert found["id"] == rel_id

    def test_find_missing(self, rel_store: RelationshipStore, entity_store: EntityStore):
        src = entity_store.create("Bob", "PERSON")
        tgt = entity_store.create("Corp", "ORGANIZATION")
        assert rel_store.find(src, tgt, "WORKS_FOR") is None

    def test_update_confidence(self, rel_store: RelationshipStore, entity_store: EntityStore):
        src = entity_store.create("C", "PERSON")
        tgt = entity_store.create("D", "ORGANIZATION")
        rel_id = rel_store.create(src, tgt, "AFFILIATED_WITH")
        rel_store.update_confidence(rel_id, 0.88)
        rows = rel_store.list_all()
        match = next(r for r in rows if r["id"] == rel_id)
        assert match["confidence_score"] == pytest.approx(0.88)

    def test_add_and_get_evidence(self, rel_store: RelationshipStore, entity_store: EntityStore, doc_store: DocumentStore, tmp_path):
        f = tmp_path / "ev.txt"
        f.write_text("x")
        doc_id = doc_store.create("ev.txt", doc_store.hash_file(f), 1, "text/plain")
        src = entity_store.create("E", "PERSON")
        tgt = entity_store.create("F", "ORGANIZATION")
        rel_id = rel_store.create(src, tgt, "WORKS_FOR")
        rel_store.add_evidence(rel_id, doc_id, "E works for F", "cooccurrence_v1", 0.5)
        evidence = rel_store.get_evidence(rel_id)
        assert len(evidence) == 1
        assert evidence[0]["passage_text"] == "E works for F"
