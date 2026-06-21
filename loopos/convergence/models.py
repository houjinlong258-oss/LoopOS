"""Loop convergence contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

LoopDecisionAction = Literal[
    "continue",
    "repair",
    "replan",
    "ask_user",
    "wait_approval",
    "halt_success",
    "halt_failure",
    "halt_blocked",
]
CriterionStatus = Literal["pending", "passed", "failed", "blocked", "not_applicable"]


class ObservationSummary(BaseModel):
    run_id: str | None = None
    step_id: str | None = None
    success: bool
    summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    run_id: str | None = None
    step_id: str | None = None
    goal_satisfied: bool = False
    failed: bool = False
    blocked: bool = False
    repairable: bool = False
    missing_information: bool = False
    regression: bool = False
    failure_type: str | None = None
    acceptance_criteria_status: dict[str, CriterionStatus] = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list)
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    reason_codes: list[str] = Field(default_factory=list)


class ProgressDelta(BaseModel):
    run_id: str | None = None
    step_id: str | None = None
    previous_score: float = Field(ge=0.0, le=1.0)
    current_score: float = Field(ge=0.0, le=1.0)
    delta: float
    no_progress_count: int = Field(default=0, ge=0)
    repeated_failures: int = Field(default=0, ge=0)
    repeated_actions: int = Field(default=0, ge=0)
    action_fingerprint: str | None = None
    evidence: list[str] = Field(default_factory=list)


class HaltCondition(BaseModel):
    reached: bool
    reason_code: str | None = None
    evidence: list[str] = Field(default_factory=list)


class LoopDecision(BaseModel):
    run_id: str | None = None
    step_id: str | None = None
    action: LoopDecisionAction
    reason_code: str
    evidence: list[str] = Field(default_factory=list)
    next_constraints: dict[str, Any] = Field(default_factory=dict)
    halt: HaltCondition = Field(default_factory=lambda: HaltCondition(reached=False))
