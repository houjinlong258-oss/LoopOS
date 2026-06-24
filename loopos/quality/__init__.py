"""Quality Engine: scoring, convergence, and delivery.

The v0.4.0 quality layer is the **measurement** layer of the loop
engineering runtime. It does not build, test, or review — those are
loop phases. It scores what the loop has produced, decides whether
to keep iterating, and emits a ``DeliveryCandidate`` when the
work is ready.

The package is deterministic, offline, and pluggable. Real scorers
can be plugged in by setting ``QualityScorer.score_fn``.
"""

from __future__ import annotations

from loopos.quality.convergence import (
    ConvergenceDecision,
    ConvergenceEngine,
    ConvergenceStatus,
    ConvergenceStatusLiteral,
)
from loopos.quality.defects import DefectTracker
from loopos.quality.delivery import DeliveryEngine
from loopos.quality.evidence import EvidenceCollector
from loopos.quality.models import (
    DeliveryCandidate,
    DeliveryStatus,
    QualityDimension,
    QualityScore,
    QualityWeights,
)
from loopos.quality.scorer import QualityScorer

__all__ = [
    "ConvergenceDecision",
    "ConvergenceEngine",
    "ConvergenceStatus",
    "ConvergenceStatusLiteral",
    "DefectTracker",
    "DeliveryCandidate",
    "DeliveryEngine",
    "DeliveryStatus",
    "EvidenceCollector",
    "QualityDimension",
    "QualityScore",
    "QualityScorer",
    "QualityWeights",
]
