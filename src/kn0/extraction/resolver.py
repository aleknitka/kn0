"""Entity resolution: match extracted entities against existing DB records."""

from __future__ import annotations

import json
from difflib import SequenceMatcher
from enum import Enum

from kn0.config import settings


class ResolutionOutcome(str, Enum):
    MERGED = "merged"         # Matched existing entity above merge_threshold
    UNDER_REVIEW = "review"   # Ambiguous match, flagged for review
    CREATED = "created"       # No match found, new entity created


def _similarity(a: str, b: str) -> float:
    """Case-insensitive token-level similarity via SequenceMatcher."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def resolve_entity(
    canonical_name: str,
    entity_type: str,
    candidates: list[dict],
    merge_threshold: float | None = None,
    review_threshold: float | None = None,
) -> tuple[ResolutionOutcome, str | None, float]:
    """
    Find the best matching existing entity for a given extracted entity.

    Returns:
        (outcome, matched_entity_id_or_None, best_score)
    """
    merge_t = merge_threshold if merge_threshold is not None else settings.merge_threshold
    review_t = review_threshold if review_threshold is not None else settings.review_threshold

    best_id: str | None = None
    best_score: float = 0.0

    name_lower = canonical_name.lower()

    for candidate in candidates:
        # 1. Exact canonical name match
        if candidate["canonical_name"].lower() == name_lower:
            return ResolutionOutcome.MERGED, candidate["id"], 1.0

        # 2. Alias match
        aliases: list[str] = json.loads(candidate.get("aliases") or "[]")
        if any(a.lower() == name_lower for a in aliases):
            return ResolutionOutcome.MERGED, candidate["id"], 0.95

        # 3. Similarity score
        score = _similarity(canonical_name, candidate["canonical_name"])
        # Also check aliases
        for alias in aliases:
            alias_score = _similarity(canonical_name, alias)
            if alias_score > score:
                score = alias_score

        if score > best_score:
            best_score = score
            best_id = candidate["id"]

    if best_score >= merge_t:
        return ResolutionOutcome.MERGED, best_id, best_score
    elif best_score >= review_t:
        return ResolutionOutcome.UNDER_REVIEW, best_id, best_score
    else:
        return ResolutionOutcome.CREATED, None, best_score
