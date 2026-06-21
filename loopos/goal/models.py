"""Structured goal negotiation contracts."""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

AmbiguityLevel = Literal["low", "medium", "high"]
GoalRisk = Literal["low", "medium", "high", "critical"]
GoalOrigin = Literal["direct", "confirmed", "selected", "merged", "manual"]


class AmbiguityReport(BaseModel):
    raw_goal: str
    ambiguous: bool = False
    level: AmbiguityLevel = "low"
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    requires_confirmation: bool = False
    requires_negotiation: bool = False
    reason_codes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def sync_legacy_fields(self) -> "AmbiguityReport":
        if not self.missing_fields and self.missing_information:
            self.missing_fields = list(self.missing_information)
        if not self.missing_information and self.missing_fields:
            self.missing_information = list(self.missing_fields)
        if not self.reason_codes and self.reasons:
            self.reason_codes = list(self.reasons)
        if not self.reasons and self.reason_codes:
            self.reasons = list(self.reason_codes)
        return self


class GoalAnalysis(AmbiguityReport):
    """Compatibility name retained for existing callers."""


class GoalOption(BaseModel):
    id: int = Field(ge=1, le=5)
    title: str
    objective: str
    scope: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    risk: GoalRisk = "low"
    estimated_steps: int = Field(default=1, ge=1)
    recommended: bool = False

    @model_validator(mode="after")
    def sync_criteria(self) -> "GoalOption":
        if not self.acceptance_criteria:
            self.acceptance_criteria = list(self.success_criteria)
        if not self.success_criteria:
            self.success_criteria = list(self.acceptance_criteria)
        return self


class GoalProposal(BaseModel):
    analysis: GoalAnalysis
    options: list[GoalOption]
    recommended_option_id: int | None = None


class GoalSpec(BaseModel):
    schema_version: str = "1.1"
    id: str = Field(default_factory=lambda: str(uuid4()))
    raw_goal: str
    objective: str
    status: Literal["finalized"] = "finalized"
    origin: GoalOrigin = "direct"
    selected_option_ids: list[int] = Field(default_factory=list)
    scope: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    risk: GoalRisk = "low"
    estimated_steps: int = Field(default=1, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("raw_goal", "objective")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("goal text cannot be empty")
        return value

    @model_validator(mode="after")
    def compatibility_defaults(self) -> "GoalSpec":
        if not self.scope:
            self.scope = [self.objective]
        if not self.acceptance_criteria:
            self.acceptance_criteria = list(self.success_criteria)
        if not self.success_criteria:
            self.success_criteria = list(self.acceptance_criteria)
        if not self.acceptance_criteria:
            self.acceptance_criteria = ["requested outcome observed", "policy constraints satisfied"]
            self.success_criteria = list(self.acceptance_criteria)
        if not self.deliverables:
            self.deliverables = ["verified goal outcome"]
        return self
