"""Pydantic schemas for Document objects."""

from __future__ import annotations

from kn0.schemas.common import KnOBaseModel


class DocumentRead(KnOBaseModel):
    """Output schema for a document record."""

    id: str
    filename: str
    file_hash: str
    file_size: int | None
    mime_type: str | None
    page_count: int | None
    language: str | None
    status: str
    source_reliability: float | None
    created_at: str
    updated_at: str
