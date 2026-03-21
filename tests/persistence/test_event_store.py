"""Tests for EventStore CRUD and timeline queries."""

from __future__ import annotations

import pytest
from kn0.persistence.store import EventStore


class TestEventStoreCreate:
    def test_create_returns_id(self, event_store: EventStore) -> None:
        event_id = event_store.create("Summit", "MEETING")
        assert isinstance(event_id, str)
        assert len(event_id) == 36

    def test_get_round_trip(self, event_store: EventStore) -> None:
        event_id = event_store.create(
            "Battle of X",
            "CONFLICT",
            description="A decisive engagement",
            start_date="1944-06-06",
            attributes={"location_note": "Normandy"},
        )
        row = event_store.get(event_id)
        assert row is not None
        assert row["title"] == "Battle of X"
        assert row["event_type"] == "CONFLICT"
        assert row["start_date"] == "1944-06-06"
        assert row["attributes"]["location_note"] == "Normandy"

    def test_get_missing_returns_none(self, event_store: EventStore) -> None:
        assert event_store.get("does-not-exist") is None

    def test_update(self, event_store: EventStore) -> None:
        event_id = event_store.create("Draft Title", "MEETING")
        event_store.update(event_id, title="Final Title", start_date="2026-01-15")
        row = event_store.get(event_id)
        assert row["title"] == "Final Title"
        assert row["start_date"] == "2026-01-15"


class TestEventStoreParticipants:
    def test_add_and_get_participant(
        self, event_store: EventStore, entity_store
    ) -> None:
        entity_id = entity_store.create("Alice", "PERSON")
        event_id = event_store.create("Meeting", "MEETING")
        event_store.add_participant(event_id, entity_id, role="ORGANIZER")

        participants = event_store.get_participants(event_id)
        assert len(participants) == 1
        assert participants[0]["entity_id"] == entity_id
        assert participants[0]["role"] == "ORGANIZER"
        assert participants[0]["canonical_name"] == "Alice"

    def test_remove_participant(self, event_store: EventStore, entity_store) -> None:
        entity_id = entity_store.create("Bob", "PERSON")
        event_id = event_store.create("Summit", "MEETING")
        event_store.add_participant(event_id, entity_id)
        event_store.remove_participant(event_id, entity_id)
        assert event_store.get_participants(event_id) == []


class TestEventStoreSourceDocuments:
    def test_add_and_get_source(
        self, event_store: EventStore, doc_store
    ) -> None:
        doc_id = doc_store.create("report.txt", "abc123", 100, "text/plain")
        event_id = event_store.create("Announcement", "ANNOUNCEMENT")
        event_store.add_source_document(
            event_id, doc_id, passage_text="The event occurred…", confidence=0.8
        )
        sources = event_store.get_source_documents(event_id)
        assert len(sources) == 1
        assert sources[0]["document_id"] == doc_id
        assert sources[0]["confidence"] == pytest.approx(0.8)


class TestEventStoreListAndTimeline:
    def _seed(self, event_store: EventStore) -> list[str]:
        ids = [
            event_store.create("Alpha", "MEETING", start_date="2024-03-01"),
            event_store.create("Beta", "CONFLICT", start_date="2024-01-15"),
            event_store.create("Gamma", "MEETING", start_date="2025-05-20"),
            event_store.create("Delta", "ELECTION"),  # undated
        ]
        return ids

    def test_list_all(self, event_store: EventStore) -> None:
        self._seed(event_store)
        rows = event_store.list_all()
        assert len(rows) == 4

    def test_list_filter_by_type(self, event_store: EventStore) -> None:
        self._seed(event_store)
        rows = event_store.list_all(event_type="MEETING")
        assert len(rows) == 2
        assert all(r["event_type"] == "MEETING" for r in rows)

    def test_list_filter_by_date_range(self, event_store: EventStore) -> None:
        self._seed(event_store)
        rows = event_store.list_all(start_date_gte="2024-02-01", start_date_lte="2024-12-31")
        assert len(rows) == 1
        assert rows[0]["title"] == "Alpha"

    def test_timeline_dated_first(self, event_store: EventStore) -> None:
        self._seed(event_store)
        rows = event_store.get_timeline()
        # undated event (Delta) must come last
        assert rows[-1]["title"] == "Delta"
        # dated events must be ascending
        dated = [r for r in rows if r["start_date"]]
        dates = [r["start_date"] for r in dated]
        assert dates == sorted(dates)

    def test_timeline_participant_count(
        self, event_store: EventStore, entity_store
    ) -> None:
        event_id = event_store.create("Big Event", "MEETING", start_date="2025-01-01")
        for name in ["Alice", "Bob", "Carol"]:
            eid = entity_store.create(name, "PERSON")
            event_store.add_participant(event_id, eid)
        rows = event_store.get_timeline()
        assert rows[0]["participant_count"] == 3

    def test_list_filter_by_entity(
        self, event_store: EventStore, entity_store
    ) -> None:
        event_id1 = event_store.create("Event A", "MEETING", start_date="2025-01-01")
        event_store.create("Event B", "CONFLICT", start_date="2025-02-01")
        entity_id = entity_store.create("Alice", "PERSON")
        event_store.add_participant(event_id1, entity_id)

        rows = event_store.list_all(entity_id=entity_id)
        assert len(rows) == 1
        assert rows[0]["id"] == event_id1

    def test_delete(self, event_store: EventStore) -> None:
        event_id = event_store.create("Temp", "OTHER")
        event_store.delete(event_id)
        assert event_store.get(event_id) is None
