"""Protocol definitions for pluggable extraction backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from kn0.extraction.entity_types import EntityType


@dataclass
class ExtractedEntity:
    text: str
    entity_type: EntityType
    start_char: int
    end_char: int
    confidence: float          # [0–1] from the NLP model
    page_number: int
    context_window: str = ""   # surrounding text for provenance


@dataclass
class ExtractedRelationship:
    source_text: str
    target_text: str
    source_type: EntityType
    target_type: EntityType
    relationship_type: str
    confidence: float
    passage: str               # text passage from which this was extracted
    page_number: int
    extraction_method: str = "cooccurrence_v1"
    context_window: str = ""


@runtime_checkable
class ExtractionBackend(Protocol):
    """Protocol for swappable NLP extraction backends."""

    def extract_entities(self, text: str, page_num: int) -> list[ExtractedEntity]:
        """Extract named entities from a text passage."""
        ...

    def extract_relationships(
        self,
        text: str,
        entities: list[ExtractedEntity],
        page_num: int,
    ) -> list[ExtractedRelationship]:
        """Extract relationships between entities in a text passage."""
        ...
