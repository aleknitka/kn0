"""Unit tests for LLMExtractionBackend — all LLM calls are mocked."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from kn0.extraction.entity_types import EntityType
from kn0.llm.extraction_backend import LLMExtractionBackend, _parse_json


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_backend(response: str) -> LLMExtractionBackend:
    """Return an LLMExtractionBackend whose client always returns ``response``."""
    client = MagicMock()
    client.chat = AsyncMock(return_value=response)
    return LLMExtractionBackend(client)


SAMPLE_TEXT = (
    "Apple Inc. was founded by Steve Jobs and Steve Wozniak in Cupertino, "
    "California in 1976."
)


# ---------------------------------------------------------------------------
# _parse_json helper
# ---------------------------------------------------------------------------

class TestParseJson:
    def test_valid_json(self) -> None:
        result = _parse_json('{"entities": []}')
        assert result == {"entities": []}

    def test_strips_markdown_fences(self) -> None:
        raw = "```json\n{\"entities\": []}\n```"
        assert _parse_json(raw) == {"entities": []}

    def test_strips_plain_fences(self) -> None:
        raw = "```\n{\"entities\": []}\n```"
        assert _parse_json(raw) == {"entities": []}

    def test_invalid_json_returns_none(self) -> None:
        assert _parse_json("not json at all") is None

    def test_non_dict_returns_none(self) -> None:
        assert _parse_json("[1, 2, 3]") is None


# ---------------------------------------------------------------------------
# Entity extraction
# ---------------------------------------------------------------------------

class TestExtractEntities:
    def test_parses_valid_json(self) -> None:
        response = json.dumps({
            "entities": [
                {"text": "Apple Inc.", "type": "ORGANIZATION", "confidence": 0.95},
                {"text": "Steve Jobs",  "type": "PERSON",       "confidence": 0.97},
            ]
        })
        backend = _make_backend(response)
        entities = backend.extract_entities(SAMPLE_TEXT, page_num=1)

        assert len(entities) == 2
        texts = {e.text for e in entities}
        assert "Apple Inc." in texts
        assert "Steve Jobs" in texts
        assert all(e.page_number == 1 for e in entities)

    def test_entity_types_resolved(self) -> None:
        response = json.dumps({
            "entities": [
                {"text": "Apple Inc.", "type": "ORGANIZATION", "confidence": 0.9},
            ]
        })
        backend = _make_backend(response)
        entities = backend.extract_entities(SAMPLE_TEXT, page_num=1)
        assert entities[0].entity_type == EntityType.ORGANIZATION

    def test_unknown_type_falls_back_to_other(self) -> None:
        response = json.dumps({
            "entities": [
                {"text": "Apple Inc.", "type": "SPACESHIP", "confidence": 0.9},
            ]
        })
        backend = _make_backend(response)
        # Unknown types that aren't in the registry are filtered out
        entities = backend.extract_entities(SAMPLE_TEXT, page_num=1)
        assert entities == []

    def test_handles_invalid_json_gracefully(self) -> None:
        backend = _make_backend("this is not valid json {{")
        entities = backend.extract_entities(SAMPLE_TEXT, page_num=1)
        assert entities == []

    def test_handles_llm_timeout_gracefully(self) -> None:
        import asyncio
        client = MagicMock()
        client.chat = AsyncMock(side_effect=asyncio.TimeoutError())
        backend = LLMExtractionBackend(client)
        # Should not raise — returns empty list
        entities = backend.extract_entities(SAMPLE_TEXT, page_num=1)
        assert entities == []


# ---------------------------------------------------------------------------
# Char offset resolution
# ---------------------------------------------------------------------------

class TestCharOffsetResolution:
    def test_offset_found(self) -> None:
        response = json.dumps({
            "entities": [{"text": "Apple Inc.", "type": "ORGANIZATION", "confidence": 0.9}]
        })
        backend = _make_backend(response)
        entities = backend.extract_entities(SAMPLE_TEXT, page_num=1)
        assert len(entities) == 1
        e = entities[0]
        assert SAMPLE_TEXT[e.start_char:e.end_char] == "Apple Inc."

    def test_offset_not_found_uses_sentinel(self) -> None:
        response = json.dumps({
            "entities": [{"text": "Nonexistent Corp XYZ", "type": "ORGANIZATION", "confidence": 0.9}]
        })
        backend = _make_backend(response)
        entities = backend.extract_entities(SAMPLE_TEXT, page_num=1)
        assert len(entities) == 1
        assert entities[0].start_char == 0
        assert entities[0].end_char == 0


# ---------------------------------------------------------------------------
# Relationship extraction
# ---------------------------------------------------------------------------

class TestExtractRelationships:
    def _make_entities(self) -> list:
        from kn0.extraction.base import ExtractedEntity
        return [
            ExtractedEntity(
                text="Steve Jobs", entity_type=EntityType.PERSON,
                start_char=0, end_char=10, confidence=0.9, page_number=1,
            ),
            ExtractedEntity(
                text="Apple Inc.", entity_type=EntityType.ORGANIZATION,
                start_char=20, end_char=30, confidence=0.9, page_number=1,
            ),
        ]

    def test_parses_valid_relationship(self) -> None:
        response = json.dumps({
            "relationships": [
                {"source": "Steve Jobs", "target": "Apple Inc.",
                 "type": "WORKS_FOR", "confidence": 0.88},
            ]
        })
        backend = _make_backend(response)
        rels = backend.extract_relationships(SAMPLE_TEXT, self._make_entities(), page_num=1)

        assert len(rels) == 1
        assert rels[0].source_text == "Steve Jobs"
        assert rels[0].target_text == "Apple Inc."
        assert rels[0].relationship_type == "WORKS_FOR"
        assert rels[0].extraction_method == "llm_v1"

    def test_unknown_rel_type_filtered(self) -> None:
        response = json.dumps({
            "relationships": [
                {"source": "Steve Jobs", "target": "Apple Inc.",
                 "type": "TELEPORTS_TO", "confidence": 0.88},
            ]
        })
        backend = _make_backend(response)
        rels = backend.extract_relationships(SAMPLE_TEXT, self._make_entities(), page_num=1)
        assert rels == []

    def test_missing_entity_filtered(self) -> None:
        response = json.dumps({
            "relationships": [
                {"source": "Elon Musk", "target": "Apple Inc.",
                 "type": "WORKS_FOR", "confidence": 0.88},
            ]
        })
        backend = _make_backend(response)
        rels = backend.extract_relationships(SAMPLE_TEXT, self._make_entities(), page_num=1)
        assert rels == []

    def test_empty_entities_returns_empty(self) -> None:
        backend = _make_backend('{"relationships": []}')
        rels = backend.extract_relationships(SAMPLE_TEXT, [], page_num=1)
        assert rels == []

    def test_invalid_json_returns_empty(self) -> None:
        backend = _make_backend("garbage response from LLM")
        rels = backend.extract_relationships(SAMPLE_TEXT, self._make_entities(), page_num=1)
        assert rels == []
