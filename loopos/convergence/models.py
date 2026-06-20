"""Loop convergence contracts."""

from __future__ import annotations

from typing import Literal

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


class ObservationSummary(BaseModel):
    success: bool
    summary: str
    evidence_refs: list[str] = Field(default_factory=list)


class EvaluationResult(BaseModel):
    goal_satisfied: bool = False
    failed: bool = False
    blocked: bool = False
    repairable: bool = False
    missing_information: bool = False
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    reason_codes: list[str] = Field(default_factory=list)


class ProgressDelta(BaseModel):
    previous_score: float = Field(ge=0.0, le=1.0)
    current_score: float = Field(ge=0.0, le=1.0)
    delta: float
    repeated_failures: int = Field(default=0, ge=0)


class HaltCondition(BaseModel):
    reached: bool
    reason_code: str | None = None


class LoopDecision(BaseModel):
    action: LoopDecisionAction
    reason_code: str
    halt: HaltCondition = Field(default_factory=lambda: HaltCondition(reached=False))

