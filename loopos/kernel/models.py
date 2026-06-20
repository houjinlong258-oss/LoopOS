"""Versioned process models for the LoopOS kernel."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from loopos.core.state import LoopState

KernelRunStatus = Literal[
    "pending",
    "running",
    "waiting_approval",
    "repairing",
    "replanning",
    "succeeded",
    "failed",
    "cancelled",
    "blocked",
]
KernelPhase = Literal[
    "BOOTING",
    "COMPILING",
    "PLANNING",
    "EXECUTING",
    "EVALUATING",
    "WAITING_APPROVAL",
    "REPAIRING",
    "REPLANNING",
    "HALTED",
]
KernelMode = Literal["guarded", "dry_run"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RunSpec(BaseModel):
    """Immutable inputs used to create one managed run."""

    goal: str
    workspace: str = "."
    mode: KernelMode = "guarded"
    max_steps: int = Field(default=20, gt=0)
    non_interactive: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("goal")
    @classmethod
    def goal_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("goal is required")
        return value


class PendingApproval(BaseModel):
    """Persisted approval request that can be resumed later."""

    instruction_id: str
    syscall_id: str | None = None
    reason_codes: list[str] = Field(default_factory=list)
    risk: Literal["medium", "high"]
    requested_at: datetime = Field(default_factory=utc_now)


class RunRecord(BaseModel):
    """Durable kernel process record."""

    model_config = ConfigDict(extra="ignore")

    schema_version: int = 2
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    goal: str
    status: KernelRunStatus = "pending"
    phase: KernelPhase = "BOOTING"
    step: int = Field(default=0, ge=0)
    max_steps: int = Field(default=20, gt=0)
    workspace: str = "."
    mode: KernelMode = "guarded"
    non_interactive: bool = False
    progress_score: float = Field(default=0.0, ge=0.0, le=1.0)
    current_instruction_id: str | None = None
    pending_approval: PendingApproval | None = None
    errors: list[str] = Field(default_factory=list)
    trace_event_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @classmethod
    def from_spec(cls, spec: RunSpec) -> "RunRecord":
        return cls(
            goal=spec.goal,
            workspace=spec.workspace,
            mode=spec.mode,
            max_steps=spec.max_steps,
            non_interactive=spec.non_interactive,
            metadata=dict(spec.metadata),
        )

    @classmethod
    def from_legacy(cls, state: LoopState) -> "RunRecord":
        return cls(
            run_id=state.run_id,
            goal=state.goal,
            status=state.status,
            phase="HALTED" if state.is_terminal else "EXECUTING",
            step=state.step_index,
            max_steps=max(state.step_index + 1, 1),
            progress_score=state.progress_score,
            current_instruction_id=state.current_instruction.id if state.current_instruction else None,
            errors=list(state.errors),
            created_at=state.created_at,
            updated_at=state.updated_at,
            metadata={"legacy_record": True},
        )

    @property
    def is_terminal(self) -> bool:
        return self.status in {"succeeded", "failed", "cancelled", "blocked"}

