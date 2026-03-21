"""Pydantic schemas for Event objects."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator, model_validator

from kn0.schemas.common import KnOBaseModel


class ParticipantRead(KnOBaseModel):
    """A single entity participant in an event, with their role."""

    entity_id: str
    canonical_name: str
    entity_type: str
    role: str | None


class EventCreate(KnOBaseModel):
    """Input schema for creating a new event."""

    title: str = Field(..., min_length=1, max_length=500)
    event_type: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    start_date: str | None = None  # ISO 8601 "YYYY-MM-DD"; None = undated
    end_date: str | None = None    # None = point-in-time event
    location_entity_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    participant_entity_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        from kn0.extraction.type_registry import event_type_registry

        if not event_type_registry.is_valid(v):
            raise ValueError(f"Unknown event type: {v!r}")
        return v.upper()

    @model_validator(mode="after")
    def validate_date_range(self) -> "EventCreate":
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValueError("start_date must be before or equal to end_date")
        return self


class EventRead(KnOBaseModel):
    """Output schema for a full event record."""

    id: str
    title: str
    event_type: str
    description: str | None
    start_date: str | None
    end_date: str | None
    location_entity_id: str | None
    attributes: dict[str, Any]
    created_at: str
    updated_at: str
    participants: list[ParticipantRead] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)


class EventSummary(KnOBaseModel):
    """Lightweight event projection for timeline list views."""

    id: str
    title: str
    event_type: str
    start_date: str | None
    end_date: str | None
    participant_count: int
