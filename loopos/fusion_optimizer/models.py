"""Fusion Optimizer data models."""

from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from loopos.loop_engine.models import (
    LoopIteration,
    LoopState,
    OptimizationPlan,
    PlanCandidate,
    RepairPlan,
    ReviewFinding,
    SuccessCriteria,
    UserGoal,
)


FusionMode = Literal["creative", "repair", "optimize", "mad_dog", "consensus"]


class FusionOptimizationRequest(BaseModel):
    """A request to the fusion optimizer."""

    model_config = ConfigDict(extra="forbid")

    goal: UserGoal
    success_criteria: SuccessCriteria
    current_state: LoopState
    previous_iteration: LoopIteration | None = None
    candidates: list[PlanCandidate] = Field(default_factory=list)
    mode: FusionMode = "consensus"


class FusionOptimizationResult(BaseModel):
    """A fusion optimization result."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"fusion_{uuid4().hex[:8]}")
    recommended_next_plan: PlanCandidate
    alternatives: list[PlanCandidate] = Field(default_factory=list)
    review_findings: list[ReviewFinding] = Field(default_factory=list)
    repair_plan: RepairPlan | None = None
    optimization_plan: OptimizationPlan | None = None
    rationale: str = ""
    disagreements: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    mode: FusionMode = "consensus"
    token_cost_estimate: int = 0
    expected_quality_gain: float = 0.0
    utility_score: float = 0.0


__all__ = [
    "FusionMode",
    "FusionOptimizationRequest",
    "FusionOptimizationResult",
]
