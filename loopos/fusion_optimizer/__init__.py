"""Fusion Optimizer: multi-candidate next-plan recommender.

The v0.4.0 fusion layer is an **optimizer**, not a verdict router.
It produces a recommended next ``PlanCandidate`` for a given
``LoopState`` and an optional list of candidates.

The package is deterministic and offline. External multi-model
fanout (e.g. OpenRouter Fusion) is **optional and pluggable** via
``candidate_factory`` on ``FusionOptimizer``. The default backend
works without any external API.
"""

from __future__ import annotations

from loopos.fusion_optimizer.candidates import (
    rank_candidates,
    score_candidate,
)
from loopos.fusion_optimizer.critique import CritiqueEngine
from loopos.fusion_optimizer.mad_dog import (
    MadDogFinding,
    MadDogReviewer,
    MadDogSeverity,
)
from loopos.fusion_optimizer.models import (
    FusionMode,
    FusionOptimizationRequest,
    FusionOptimizationResult,
)
from loopos.fusion_optimizer.optimizer import FusionOptimizer
from loopos.fusion_optimizer.resolver import Resolver
from loopos.fusion_optimizer.verifier import EvidenceVerifier

__all__ = [
    "CritiqueEngine",
    "EvidenceVerifier",
    "FusionMode",
    "FusionOptimizationRequest",
    "FusionOptimizationResult",
    "FusionOptimizer",
    "MadDogFinding",
    "MadDogReviewer",
    "MadDogSeverity",
    "Resolver",
    "rank_candidates",
    "score_candidate",
]
