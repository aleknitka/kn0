"""Pydantic schemas for Relationship objects."""

from __future__ import annotations

from pydantic import Field, field_validator

from kn0.schemas.common import KnOBaseModel


class RelationshipCreate(KnOBaseModel):
    """Input schema for creating a new relationship."""

    source_entity_id: str
    target_entity_id: str
    relationship_type: str = Field(..., min_length=1, max_length=100)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("relationship_type")
    @classmethod
    def validate_relationship_type(cls, v: str) -> str:
        from kn0.extraction.type_registry import relationship_type_registry

        if not relationship_type_registry.is_valid(v):
            raise ValueError(f"Unknown relationship type: {v!r}")
        return v.upper()


class RelationshipRead(KnOBaseModel):
    """Output schema for a full relationship record."""

    id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    confidence_score: float
    status: str
    first_seen: str
    last_confirmed: str
