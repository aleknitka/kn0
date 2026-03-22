"""Prompt templates for LLM-based entity and relationship extraction."""

from __future__ import annotations

ENTITY_SYSTEM_PROMPT = """\
You are an expert information extraction assistant. Your task is to extract named entities from the provided text.

Return ONLY a valid JSON object in exactly this format — no explanation, no markdown, no code fences:
{{
  "entities": [
    {{"text": "<exact text span from the document>", "type": "<TYPE>", "confidence": <0.0-1.0>}}
  ]
}}

Valid entity types: {valid_types}

Rules:
- "text" must be the exact substring as it appears in the input text (preserve original casing and spacing)
- "type" must be one of the valid types listed above
- "confidence" is your certainty that this is a correct entity extraction (0.0 to 1.0)
- Extract all meaningful named entities; omit common nouns and generic references
- If no entities are found, return {{"entities": []}}
"""

ENTITY_USER_PROMPT = """\
Extract all named entities from the following text:

{text}
"""

RELATIONSHIP_SYSTEM_PROMPT = """\
You are an expert information extraction assistant. Your task is to identify relationships between named entities in the provided text.

You will be given:
1. A passage of text
2. A list of entities already extracted from that text

Return ONLY a valid JSON object in exactly this format — no explanation, no markdown, no code fences:
{{
  "relationships": [
    {{"source": "<entity text>", "target": "<entity text>", "type": "<TYPE>", "confidence": <0.0-1.0>}}
  ]
}}

Valid relationship types: {valid_types}

Rules:
- "source" and "target" must exactly match one of the entity texts provided
- "type" must be one of the valid relationship types listed above
- "confidence" is your certainty that this relationship exists in the text (0.0 to 1.0)
- Only extract relationships that are explicitly or strongly implied in the text
- If no relationships are found, return {{"relationships": []}}
"""

RELATIONSHIP_USER_PROMPT = """\
Text passage:
{text}

Entities found in this passage:
{entity_list}

Extract all relationships between these entities that are supported by the text.
"""


def build_entity_system_prompt(valid_types: list[str]) -> str:
    """Inject valid type list into the entity system prompt."""
    return ENTITY_SYSTEM_PROMPT.format(valid_types=", ".join(valid_types))


def build_entity_user_prompt(text: str) -> str:
    return ENTITY_USER_PROMPT.format(text=text)


def build_relationship_system_prompt(valid_types: list[str]) -> str:
    """Inject valid type list into the relationship system prompt."""
    return RELATIONSHIP_SYSTEM_PROMPT.format(valid_types=", ".join(valid_types))


def build_relationship_user_prompt(text: str, entity_texts: list[str]) -> str:
    entity_list = "\n".join(f"- {e}" for e in entity_texts)
    return RELATIONSHIP_USER_PROMPT.format(text=text, entity_list=entity_list)
