"""Confidence scoring for extracted relationships.

Formula (from PRD §6.3.3):
    final = 0.40 * extraction_confidence
          + 0.35 * corroboration_score
          + 0.25 * source_reliability

Where:
    corroboration_score = min(1.0, log(1 + confirming_doc_count) / log(10))
    source_reliability  = user-configured per-document weight [0–1]
"""

from __future__ import annotations

import math


WEIGHT_EXTRACTION = 0.40
WEIGHT_CORROBORATION = 0.35
WEIGHT_SOURCE = 0.25


def corroboration_score(confirming_doc_count: int) -> float:
    """Logarithmic boost for multiple independent confirming documents."""
    return min(1.0, math.log1p(confirming_doc_count) / math.log(10))


def compute_confidence(
    extraction_confidence: float,
    confirming_doc_count: int,
    source_reliability: float,
) -> float:
    """Calculate composite confidence score for a relationship."""
    corr = corroboration_score(confirming_doc_count)
    score = (
        WEIGHT_EXTRACTION * extraction_confidence
        + WEIGHT_CORROBORATION * corr
        + WEIGHT_SOURCE * source_reliability
    )
    return round(min(1.0, max(0.0, score)), 4)


def recalculate_from_evidence(
    evidence_list: list[dict],
    source_reliability_map: dict[str, float],
) -> float:
    """
    Recalculate confidence from a list of evidence records.

    evidence_list: list of dicts with 'individual_confidence', 'document_id', 'validation_status'
    source_reliability_map: document_id → source_reliability weight
    """
    active_evidence = [
        e for e in evidence_list
        if e.get("validation_status") not in ("disputed", "irrelevant")
    ]
    if not active_evidence:
        return 0.0

    # Average extraction confidence across active evidence
    avg_extraction = sum(e["individual_confidence"] for e in active_evidence) / len(active_evidence)

    # Count distinct confirming documents
    confirming_docs = len({e["document_id"] for e in active_evidence})

    # Average source reliability across documents that contributed evidence
    reliabilities = [
        source_reliability_map.get(e["document_id"], 0.5)
        for e in active_evidence
    ]
    avg_reliability = sum(reliabilities) / len(reliabilities)

    return compute_confidence(avg_extraction, confirming_docs, avg_reliability)
