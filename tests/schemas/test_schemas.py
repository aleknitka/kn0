"""Tests for Pydantic schemas: validation and serialization."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from kn0.schemas import EntityCreate, EventCreate, RelationshipCreate


class TestEntityCreate:
    def test_valid_builtin_type(self) -> None:
        e = EntityCreate(canonical_name="Alice", entity_type="PERSON")
        assert e.entity_type == "PERSON"

    def test_case_insensitive_type(self) -> None:
        e = EntityCreate(canonical_name="ACME Corp", entity_type="organization")
        assert e.entity_type == "ORGANIZATION"

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValidationError, match="Unknown entity type"):
            EntityCreate(canonical_name="X", entity_type="SPACESHIP")

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            EntityCreate(canonical_name="", entity_type="PERSON")

    def test_defaults(self) -> None:
        e = EntityCreate(canonical_name="Bob", entity_type="PERSON")
        assert e.aliases == []
        assert e.attributes == {}


class TestRelationshipCreate:
    def test_valid(self) -> None:
        r = RelationshipCreate(
            source_entity_id="aaa",
            target_entity_id="bbb",
            relationship_type="WORKS_FOR",
        )
        assert r.confidence_score == 0.0

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValidationError, match="Unknown relationship type"):
            RelationshipCreate(
                source_entity_id="a",
                target_entity_id="b",
                relationship_type="TELEPORTS_TO",
            )

    def test_confidence_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            RelationshipCreate(
                source_entity_id="a",
                target_entity_id="b",
                relationship_type="KNOWS",
                confidence_score=1.5,
            )


class TestEventCreate:
    def test_valid_minimal(self) -> None:
        ev = EventCreate(title="Board Meeting", event_type="MEETING")
        assert ev.event_type == "MEETING"
        assert ev.start_date is None

    def test_case_insensitive_type(self) -> None:
        ev = EventCreate(title="Annual election", event_type="election")
        assert ev.event_type == "ELECTION"

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValidationError, match="Unknown event type"):
            EventCreate(title="X", event_type="ALIEN_INVASION")

    def test_valid_date_range(self) -> None:
        ev = EventCreate(
            title="War", event_type="CONFLICT",
            start_date="2000-01-01", end_date="2002-06-15",
        )
        assert ev.start_date == "2000-01-01"

    def test_invalid_date_range_raises(self) -> None:
        with pytest.raises(ValidationError, match="start_date must be before"):
            EventCreate(
                title="Impossible",
                event_type="OTHER",
                start_date="2005-01-01",
                end_date="2003-01-01",
            )

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            EventCreate(title="X", event_type="MEETING", unknown_field="oops")  # type: ignore[call-arg]
