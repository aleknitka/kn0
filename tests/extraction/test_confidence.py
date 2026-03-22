"""Tests for confidence scoring."""

import math

import pytest

from kn0.extraction.confidence import (
    compute_confidence,
    corroboration_score,
    recalculate_from_evidence,
)


def test_corroboration_zero_docs():
    assert corroboration_score(0) == 0.0


def test_corroboration_one_doc():
    score = corroboration_score(1)
    assert score == pytest.approx(math.log(2) / math.log(10), rel=1e-4)


def test_corroboration_capped_at_one():
    # With 10+ docs it should approach 1.0
    assert corroboration_score(1000) == 1.0


def test_compute_confidence_bounds():
    score = compute_confidence(0.8, 3, 0.7)
    assert 0.0 <= score <= 1.0


def test_compute_confidence_zero_extraction():
    score = compute_confidence(0.0, 0, 0.0)
    assert score == 0.0


def test_compute_confidence_formula():
    ext = 0.8
    corr = corroboration_score(2)
    src = 0.6
    expected = 0.40 * ext + 0.35 * corr + 0.25 * src
    assert compute_confidence(ext, 2, src) == pytest.approx(expected, rel=1e-4)


def test_recalculate_from_evidence_empty():
    assert recalculate_from_evidence([], {}) == 0.0


def test_recalculate_excludes_disputed():
    evidence = [
        {"individual_confidence": 0.9, "document_id": "doc1", "validation_status": "confirmed"},
        {"individual_confidence": 0.9, "document_id": "doc2", "validation_status": "disputed"},
    ]
    reliability_map = {"doc1": 0.8, "doc2": 0.8}
    score_with_dispute = recalculate_from_evidence(evidence, reliability_map)
    score_without = recalculate_from_evidence([evidence[0]], {"doc1": 0.8})
    assert score_with_dispute == pytest.approx(score_without, rel=1e-4)
