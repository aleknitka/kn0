"""LLM-powered extraction backend implementing the ExtractionBackend Protocol."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from kn0.extraction.base import ExtractedEntity, ExtractedRelationship
from kn0.extraction.entity_types import EntityType
from kn0.extraction.type_registry import (
    entity_type_registry,
    relationship_type_registry,
)
from kn0.llm.client import LLMClient
from kn0.llm.prompts import (
    build_entity_system_prompt,
    build_entity_user_prompt,
    build_relationship_system_prompt,
    build_relationship_user_prompt,
)

logger = logging.getLogger(__name__)


def _resolve_char_offsets(text: str, span: str) -> tuple[int, int]:
    """Locate ``span`` inside ``text``; return (start, end) or (0, 0) sentinel."""
    idx = text.find(span)
    if idx == -1:
        idx = text.lower().find(span.lower())
    if idx == -1:
        return 0, 0
    return idx, idx + len(span)


def _to_entity_type(type_str: str) -> EntityType:
    """Map a string to EntityType, falling back to OTHER for unknown values."""
    normalised = type_str.upper()
    try:
        return EntityType(normalised)
    except ValueError:
        return EntityType.OTHER


class LLMExtractionBackend:
    """Extraction backend that uses an LLM for NER and relationship extraction.

    The public ``extract_entities`` and ``extract_relationships`` methods are
    synchronous to satisfy the ``ExtractionBackend`` Protocol used by the
    current CLI pipeline.  Internally they drive async coroutines via
    ``asyncio.run()``.

    When the Phase-2 REST API is available, callers can use the ``_async``
    variants directly without the ``asyncio.run()`` overhead.
    """

    def __init__(self, client: LLMClient) -> None:
        self._client = client
        self._entity_system = build_entity_system_prompt(entity_type_registry.all_types())
        self._rel_system = build_relationship_system_prompt(
            relationship_type_registry.all_types()
        )

    # ------------------------------------------------------------------
    # Public sync interface (ExtractionBackend Protocol)
    # ------------------------------------------------------------------

    def extract_entities(self, text: str, page_num: int) -> list[ExtractedEntity]:
        """Extract entities synchronously by driving the async implementation."""
        try:
            return asyncio.run(self._extract_entities_async(text, page_num))
        except Exception as exc:
            logger.warning("LLM entity extraction failed on page %d: %s", page_num, exc)
            return []

    def extract_relationships(
        self,
        text: str,
        entities: list[ExtractedEntity],
        page_num: int,
    ) -> list[ExtractedRelationship]:
        """Extract relationships synchronously by driving the async implementation."""
        try:
            return asyncio.run(self._extract_relationships_async(text, entities, page_num))
        except Exception as exc:
            logger.warning(
                "LLM relationship extraction failed on page %d: %s", page_num, exc
            )
            return []

    # ------------------------------------------------------------------
    # Async implementations (usable directly from async callers)
    # ------------------------------------------------------------------

    async def _extract_entities_async(
        self, text: str, page_num: int
    ) -> list[ExtractedEntity]:
        raw = await self._client.chat(
            system=self._entity_system,
            user=build_entity_user_prompt(text),
        )
        data = _parse_json(raw)
        if data is None:
            return []

        results: list[ExtractedEntity] = []
        for item in data.get("entities", []):
            span: str = item.get("text", "").strip()
            type_str: str = item.get("type", "OTHER")
            confidence: float = float(item.get("confidence", 0.75))

            if not span or not entity_type_registry.is_valid(type_str):
                continue

            start, end = _resolve_char_offsets(text, span)
            # Capture surrounding context (up to 100 chars each side)
            ctx_start = max(0, start - 100)
            ctx_end = min(len(text), end + 100)
            context = text[ctx_start:ctx_end]

            results.append(
                ExtractedEntity(
                    text=span,
                    entity_type=_to_entity_type(type_str),
                    start_char=start,
                    end_char=end,
                    confidence=max(0.0, min(1.0, confidence)),
                    page_number=page_num,
                    context_window=context,
                )
            )
        return results

    async def _extract_relationships_async(
        self,
        text: str,
        entities: list[ExtractedEntity],
        page_num: int,
    ) -> list[ExtractedRelationship]:
        if not entities:
            return []

        entity_texts = list({e.text for e in entities})
        entity_map: dict[str, ExtractedEntity] = {e.text: e for e in entities}

        raw = await self._client.chat(
            system=self._rel_system,
            user=build_relationship_user_prompt(text, entity_texts),
        )
        data = _parse_json(raw)
        if data is None:
            return []

        results: list[ExtractedRelationship] = []
        for item in data.get("relationships", []):
            source_text: str = item.get("source", "").strip()
            target_text: str = item.get("target", "").strip()
            rel_type: str = item.get("type", "").strip().upper()
            confidence: float = float(item.get("confidence", 0.6))

            source_entity = entity_map.get(source_text)
            target_entity = entity_map.get(target_text)

            if not source_entity or not target_entity:
                continue
            if not relationship_type_registry.is_valid(rel_type):
                continue

            results.append(
                ExtractedRelationship(
                    source_text=source_text,
                    target_text=target_text,
                    source_type=source_entity.entity_type,
                    target_type=target_entity.entity_type,
                    relationship_type=rel_type,
                    confidence=max(0.0, min(1.0, confidence)),
                    passage=text[:500],  # first 500 chars as provenance
                    page_number=page_num,
                    extraction_method="llm_v1",
                )
            )
        return results


def _parse_json(raw: str) -> dict[str, Any] | None:
    """Parse JSON from LLM response, stripping markdown fences if present."""
    text = raw.strip()
    # Strip common markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else None
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse LLM JSON response: %s | raw: %.200s", exc, raw)
        return None


def get_llm_backend(settings: Any = None) -> LLMExtractionBackend:
    """Build an LLMExtractionBackend from kn0 settings."""
    if settings is None:
        from kn0.config import settings as _settings
        settings = _settings

    client = LLMClient(
        provider=settings.llm_provider,
        model=settings.llm_model,
        base_url=settings.llm_base_url or None,
        api_key=settings.llm_api_key or None,
        temperature=settings.llm_temperature,
        timeout=settings.llm_timeout,
    )
    return LLMExtractionBackend(client)
