"""spaCy-based NER and co-occurrence relationship extraction."""

from __future__ import annotations

import re

from kn0.extraction.base import ExtractionBackend, ExtractedEntity, ExtractedRelationship
from kn0.extraction.entity_types import EntityType, SPACY_LABEL_MAP

# Relationship types assigned to co-occurring entity pairs by their type combination
_COOC_RELATIONSHIP_MAP: dict[tuple[EntityType, EntityType], str] = {
    (EntityType.PERSON, EntityType.ORGANIZATION): "AFFILIATED_WITH",
    (EntityType.ORGANIZATION, EntityType.PERSON): "EMPLOYS",
    (EntityType.PERSON, EntityType.LOCATION): "LOCATED_IN",
    (EntityType.ORGANIZATION, EntityType.LOCATION): "BASED_IN",
    (EntityType.PERSON, EntityType.DATE): "ASSOCIATED_WITH",
    (EntityType.ORGANIZATION, EntityType.DATE): "ACTIVE_AT",
    (EntityType.ORGANIZATION, EntityType.MONETARY): "FINANCIAL_RELATION",
    (EntityType.PERSON, EntityType.MONETARY): "FINANCIAL_RELATION",
    (EntityType.EVENT, EntityType.PERSON): "INVOLVES",
    (EntityType.EVENT, EntityType.ORGANIZATION): "INVOLVES",
    (EntityType.EVENT, EntityType.LOCATION): "OCCURRED_IN",
    (EntityType.EVENT, EntityType.DATE): "OCCURRED_AT",
}

_DEFAULT_RELATIONSHIP = "CO_OCCURS_WITH"

# Confidence assigned to co-occurrence relationships (lower than model-based RE)
_COOC_CONFIDENCE = 0.45


class SpacyBackend:
    """Extraction backend backed by a spaCy pipeline."""

    def __init__(self, model_name: str = "en_core_web_sm") -> None:
        self._model_name = model_name
        self._nlp = None  # Lazy-load

    def _get_nlp(self):
        if self._nlp is None:
            try:
                import spacy
                self._nlp = spacy.load(self._model_name)
            except OSError as e:
                raise RuntimeError(
                    f"spaCy model {self._model_name!r} not found. "
                    f"Run: python -m spacy download {self._model_name}"
                ) from e
        return self._nlp

    def extract_entities(self, text: str, page_num: int) -> list[ExtractedEntity]:
        nlp = self._get_nlp()
        doc = nlp(text)
        results: list[ExtractedEntity] = []

        for ent in doc.ents:
            entity_type = SPACY_LABEL_MAP.get(ent.label_, EntityType.OTHER)
            if entity_type == EntityType.OTHER:
                continue

            # Build a context window (sentence containing the entity)
            sent_text = ent.sent.text if ent.sent else ""

            results.append(
                ExtractedEntity(
                    text=ent.text.strip(),
                    entity_type=entity_type,
                    start_char=ent.start_char,
                    end_char=ent.end_char,
                    confidence=0.75,  # spaCy doesn't expose per-ent confidence; use a fixed estimate
                    page_number=page_num,
                    context_window=sent_text,
                )
            )
        return results

    def extract_relationships(
        self,
        text: str,
        entities: list[ExtractedEntity],
        page_num: int,
    ) -> list[ExtractedRelationship]:
        """Extract co-occurrence relationships from entities in the same sentence."""
        nlp = self._get_nlp()
        doc = nlp(text)
        results: list[ExtractedRelationship] = []

        # Group entities by sentence
        for sent in doc.sents:
            sent_start = sent.start_char
            sent_end = sent.end_char
            sent_entities = [
                e for e in entities
                if sent_start <= e.start_char < sent_end
            ]

            # Generate pairs within the same sentence
            for i, src in enumerate(sent_entities):
                for tgt in sent_entities[i + 1 :]:
                    if src.text == tgt.text:
                        continue
                    rel_type = _COOC_RELATIONSHIP_MAP.get(
                        (src.entity_type, tgt.entity_type),
                        _DEFAULT_RELATIONSHIP,
                    )
                    results.append(
                        ExtractedRelationship(
                            source_text=src.text,
                            target_text=tgt.text,
                            source_type=src.entity_type,
                            target_type=tgt.entity_type,
                            relationship_type=rel_type,
                            confidence=_COOC_CONFIDENCE,
                            passage=sent.text,
                            page_number=page_num,
                            extraction_method="cooccurrence_v1",
                            context_window=sent.text,
                        )
                    )
        return results


# Default backend instance (lazy-initialized)
_default_backend: SpacyBackend | None = None


def get_default_backend(model_name: str = "en_core_web_sm") -> SpacyBackend:
    global _default_backend
    if _default_backend is None:
        _default_backend = SpacyBackend(model_name=model_name)
    return _default_backend
