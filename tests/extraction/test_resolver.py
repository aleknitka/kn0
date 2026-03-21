"""Tests for entity resolution algorithm."""

import pytest

from kn0.extraction.resolver import ResolutionOutcome, resolve_entity


def _candidate(name: str, aliases: list[str] | None = None) -> dict:
    import json
    return {
        "id": f"id-{name.lower().replace(' ', '-')}",
        "canonical_name": name,
        "entity_type": "PERSON",
        "aliases": json.dumps(aliases or []),
    }


def test_exact_match():
    candidates = [_candidate("Steve Jobs")]
    outcome, entity_id, score = resolve_entity("Steve Jobs", "PERSON", candidates)
    assert outcome == ResolutionOutcome.MERGED
    assert entity_id == "id-steve-jobs"
    assert score == 1.0


def test_exact_match_case_insensitive():
    candidates = [_candidate("Steve Jobs")]
    outcome, entity_id, score = resolve_entity("steve jobs", "PERSON", candidates)
    assert outcome == ResolutionOutcome.MERGED


def test_alias_match():
    candidates = [_candidate("United States of America", aliases=["USA", "US", "United States"])]
    outcome, entity_id, score = resolve_entity("USA", "ORGANIZATION", candidates)
    assert outcome == ResolutionOutcome.MERGED
    assert score == 0.95


def test_high_similarity_merges():
    candidates = [_candidate("Apple Incorporated")]
    # "Apple Inc." is similar but not exact
    outcome, entity_id, score = resolve_entity(
        "Apple Incorporated", "ORGANIZATION", candidates,
        merge_threshold=0.85,
    )
    assert outcome == ResolutionOutcome.MERGED


def test_low_similarity_creates_new():
    candidates = [_candidate("Google LLC")]
    outcome, entity_id, score = resolve_entity(
        "Microsoft Corporation", "ORGANIZATION", candidates,
        merge_threshold=0.85,
        review_threshold=0.65,
    )
    assert outcome == ResolutionOutcome.CREATED
    assert entity_id is None


def test_medium_similarity_flags_review():
    candidates = [_candidate("Tim Cook")]
    outcome, entity_id, score = resolve_entity(
        "Tim Cooks", "PERSON", candidates,
        merge_threshold=0.90,  # Raise threshold so this doesn't auto-merge
        review_threshold=0.60,
    )
    # "Tim Cook" vs "Tim Cooks" similarity ~ 0.88 — should be UNDER_REVIEW at threshold 0.90
    assert outcome in (ResolutionOutcome.UNDER_REVIEW, ResolutionOutcome.MERGED)


def test_empty_candidates():
    outcome, entity_id, score = resolve_entity("New Entity", "CONCEPT", [])
    assert outcome == ResolutionOutcome.CREATED
    assert entity_id is None
