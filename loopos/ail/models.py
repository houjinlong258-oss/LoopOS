"""Pydantic models for LoopOS Agent Internal Language."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from loopos.core.isa import ExpectedObservation, InstructionOp, InstructionSafety
from loopos.core.state import EvaluationStatus, RunStatus
from loopos.memory.belief_store import MemoryLayer, MemoryScope, MemoryStatus, MemoryType

RenderFormat = Literal["text", "json", "markdown"]
RenderVerbosity = Literal["quiet", "normal", "verbose"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AILGoal(BaseModel):
    """Structured goal at the runtime boundary."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    text: str
    source: str = "user"
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("text", "source")
    @classmethod
    def non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value


class AILState(BaseModel):
    """Compact state shape used between loop phases."""

    run_id: str
    status: RunStatus
    step_index: int = 0
    progress_score: float = 0.0
    current_instruction_id: str | None = None
    memory_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AILInstruction(BaseModel):
    """Canonical internal instruction object."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()))
    op: InstructionOp
    created_at: datetime = Field(default_factory=utc_now)
    reason_code: str
    args: dict[str, Any] = Field(default_factory=dict)
    safety: InstructionSafety = Field(default_factory=InstructionSafety)
    expected_observation: ExpectedObservation = Field(default_factory=ExpectedObservation)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("reason_code")
    @classmethod
    def reason_code_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason_code is required")
        return value

    @model_validator(mode="after")
    def validate_instruction_contract(self) -> "AILInstruction":
        from loopos.ail.validators import validate_ail_instruction

        issues = validate_ail_instruction(self)
        if issues:
            raise ValueError("; ".join(issues))
        return self


class AILObservation(BaseModel):
    """Normalized result from executing an AIL instruction."""

    instruction_id: str
    success: bool
    summary: str
    stdout: str = ""
    stderr: str = ""
    return_code: int | None = None
    duration_ms: int = 0
    error: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class AILEvaluation(BaseModel):
    """Structured critic/evaluator output."""

    status: EvaluationStatus
    score_delta: float = 0.0
    summary: str = ""
    memory_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AILEvent(BaseModel):
    """Typed event emitted by the runtime loop."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    type: str
    run_id: str
    step_index: int
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class AILMemory(BaseModel):
    """Memory object shape exposed to AIL."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    type: MemoryType
    content: str
    confidence: float
    source: str
    layer: MemoryLayer = "belief"
    scope: MemoryScope = "project"
    status: MemoryStatus = "active"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AILSkill(BaseModel):
    """Reusable skill description available to the loop."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    trigger_tags: list[str] = Field(default_factory=list)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.5
    metadata: dict[str, Any] = Field(default_factory=dict)


class AILPreference(BaseModel):
    """User or project preference usable by policy and render phases."""

    key: str
    value: str
    scope: MemoryScope = "user"
    confidence: float = 1.0
    source: str = "user_profile"
    metadata: dict[str, Any] = Field(default_factory=dict)


class AILRenderSpec(BaseModel):
    """Renderer contract for final human-facing output."""

    format: RenderFormat = "text"
    verbosity: RenderVerbosity = "normal"
    include_json: bool = False
    hints: dict[str, Any] = Field(default_factory=dict)
