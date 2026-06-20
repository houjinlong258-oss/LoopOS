"""Structured goal negotiation contracts."""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class GoalAnalysis(BaseModel):
    raw_goal: str
    ambiguous: bool
    reasons: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


class GoalOption(BaseModel):
    id: int = Field(ge=1, le=5)
    title: str
    objective: str
    success_criteria: list[str] = Field(default_factory=list)


class GoalProposal(BaseModel):
    analysis: GoalAnalysis
    options: list[GoalOption]


class GoalSpec(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    raw_goal: str
    objective: str
    status: Literal["finalized"] = "finalized"
    selected_option_ids: list[int] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("raw_goal", "objective")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("goal text cannot be empty")
        return value

