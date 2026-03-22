"""Pydantic schemas for Entity objects."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from kn0.schemas.common import KnOBaseModel


class EntityCreate(KnOBaseModel):
    """Input schema for creating a new entity."""

    canonical_name: str = Field(..., min_length=1, max_length=500)
    entity_type: str
    aliases: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        from kn0.extraction.type_registry import entity_type_registry

        if not entity_type_registry.is_valid(v):
            raise ValueError(f"Unknown entity type: {v!r}")
        return v.upper()


class EntityRead(KnOBaseModel):
    """Output schema for a full entity record."""

    id: str
    canonical_name: str
    entity_type: str
    aliases: list[str]
    attributes: dict[str, Any]
    mention_count: int
    first_seen: str
    last_updated: str


class EntitySummary(KnOBaseModel):
    """Lightweight entity projection for list views."""

    id: str
    canonical_name: str
    entity_type: str
    mention_count: int
