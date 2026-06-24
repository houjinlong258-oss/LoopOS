"""Quality Engine data models."""

from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


QualityDimension = Literal[
    "goal_alignment",
    "test_health",
    "defect_health",
    "design_health",
    "documentation_health",
    "delivery_readiness",
]


class QualityWeights(BaseModel):
    """Per-dimension weights for the overall quality score."""

    model_config = ConfigDict(extra="forbid")

    goal_alignment: float = 0.30
    test_health: float = 0.25
    defect_health: float = 0.20
    design_health: float = 0.10
    documentation_health: float = 0.05
    delivery_readiness: float = 0.10

    def total(self) -> float:
        return (
            self.goal_alignment + self.test_health + self.defect_health
            + self.design_health + self.documentation_health
            + self.delivery_readiness
        )


class QualityScore(BaseModel):
    """A six-dimension quality score plus a weighted overall."""

    model_config = ConfigDict(extra="forbid")

    overall: float = 0.0
    goal_alignment: float = 0.0
    test_health: float = 0.0
    defect_health: float = 0.0
    design_health: float = 0.0
    documentation_health: float = 0.0
    delivery_readiness: float = 0.0
    reasons: list[str] = Field(default_factory=list)


ConvergenceStatusLiteral = Literal[
    "continue", "deliver", "blocked", "iteration_budget_exhausted",
]


class ConvergenceStatus(BaseModel):
    """The convergence decision for a single loop iteration."""

    model_config = ConfigDict(extra="forbid")

    status: ConvergenceStatusLiteral = "continue"
    reason: str = ""
    satisfied_criteria: list[str] = Field(default_factory=list)
    unsatisfied_criteria: list[str] = Field(default_factory=list)
    next_recommended_action: str | None = None


DeliveryStatus = Literal["ready", "not_ready", "blocked", "deferred"]


class DeliveryCandidate(BaseModel):
    """A candidate delivery artifact, with evidence and risks."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"delivery_{uuid4().hex[:8]}")
    goal_id: str
    summary: str
    evidence: list[str] = Field(default_factory=list)
    quality_score: QualityScore
    known_limitations: list[str] = Field(default_factory=list)
    open_risks: list[str] = Field(default_factory=list)
    ready: bool = False
    status: DeliveryStatus = "not_ready"


__all__ = [
    "DeliveryCandidate",
    "DeliveryStatus",
    "QualityDimension",
    "QualityScore",
    "QualityWeights",
]
