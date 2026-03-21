"""Shared Pydantic base model for kn0 schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class KnOBaseModel(BaseModel):
    """Project-wide Pydantic base: forbid extras, populate from ORM attributes."""

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        populate_by_name=True,
    )
