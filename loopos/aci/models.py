"""Typed schemas for the Agent Command Interface.

An :class:`AgentCommand` is the contract an agent submits to LoopOS.
An :class:`AgentCommandResult` is the structured response that the
runtime returns. Both have stable JSON contracts so the wire format
remains testable, replayable, and agent-portable.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from loopos.policy_os.models import PolicyDecision

# ----- Command taxonomy ---------------------------------------------------

AgentCommandKind = Literal[
    "terminal.exec",
    "file.read",
    "file.write",
    "git.status",
    "git.diff",
    "database.query",
    "database.run_migration",
    "noop",
]

AgentCommandMode = Literal["guarded", "dry_run"]

AgentCommandStatus = Literal[
    "completed",
    "blocked",
    "failed",
    "approval_required",
    "dry_run",
]

ObservationKind = Literal["command_result", "file_content", "git_state", "database_result", "noop"]

ConvergenceHint = Literal[
    "continue",
    "repair",
    "replan",
    "ask_user",
    "wait_approval",
    "halt_success",
    "halt_failure",
    "halt_blocked",
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ----- Sub-models ---------------------------------------------------------


class CommandCapability(BaseModel):
    """Capability hints declared by the agent for a command.

    The runner cross-checks these against the runtime capability
    boundary. A mismatch produces a structured denial, never a
    silent override.
    """

    model_config = ConfigDict(extra="forbid")

    filesystem_read: bool = False
    filesystem_write: bool = False
    network: bool = False
    database: bool = False
    tags: list[str] = Field(default_factory=list)


class ObservationSummary(BaseModel):
    """Structured observation attached to a command result."""

    model_config = ConfigDict(extra="forbid")

    kind: ObservationKind = "command_result"
    success: bool = False
    summary: str = ""
    return_code: int | None = None
    duration_ms: int = 0
    stdout: str = ""
    stderr: str = ""
    data: dict[str, Any] = Field(default_factory=dict)


class ProgressSnapshot(BaseModel):
    """Progress hint attached to a command result.

    The runner fills this from the runtime evidence when available.
    When the runtime is not available (e.g. in explain mode or in
    Phase 1 without Kernel integration) the runner emits a
    deterministic placeholder.
    """

    model_config = ConfigDict(extra="forbid")

    previous_score: float = Field(default=0.0, ge=0.0, le=1.0)
    current_score: float = Field(default=0.0, ge=0.0, le=1.0)
    no_progress: bool = False
    placeholder: bool = True


class EvaluationHint(BaseModel):
    """Evaluation hint attached to a command result.

    A non-Kernel integration cannot produce a real :class:`Evaluation`
    object, so ACI carries a compact hint with the minimum evidence
    the runtime needs to drive the next convergence decision.
    """

    model_config = ConfigDict(extra="forbid")

    goal_satisfied: bool = False
    failed: bool = False
    repairable: bool = False
    missing_information: bool = False
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reason_codes: list[str] = Field(default_factory=list)
    placeholder: bool = True


class ConvergenceSnapshot(BaseModel):
    """Convergence hint attached to a command result."""

    model_config = ConfigDict(extra="forbid")

    action: ConvergenceHint = "continue"
    reason_code: str = "aci.no_kernel_runtime"
    placeholder: bool = True


# ----- Top-level models ---------------------------------------------------


class AgentCommand(BaseModel):
    """Single agent command submitted to the ACI layer.

    Required fields: ``goal_id``, ``purpose``, ``kind``, ``command``.
    Optional fields let the agent declare constraints, capabilities,
    approval grants, and metadata without bypassing the runtime.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()))
    goal_id: str
    purpose: str
    kind: AgentCommandKind
    command: str
    args: dict[str, Any] = Field(default_factory=dict)
    mode: AgentCommandMode = "guarded"
    capabilities: CommandCapability = Field(default_factory=CommandCapability)
    timeout_seconds: int | None = Field(default=None, ge=1)
    expected_observation: str = "command_result"
    approval_granted: bool = False
    dry_run: bool = False
    created_at: datetime = Field(default_factory=_utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("goal_id", "purpose", "kind", "command")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("value is required and must be non-empty")
        return value

    @field_validator("expected_observation")
    @classmethod
    def observation_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("expected_observation is required")
        return value

    @model_validator(mode="after")
    def dry_run_sets_mode(self) -> "AgentCommand":
        if self.dry_run and self.mode != "dry_run":
            object.__setattr__(self, "mode", "dry_run")
        return self


class AgentCommandResult(BaseModel):
    """Structured response returned by the ACI runner.

    The shape is stable across versions and matches the existing
    ``PolicyDecision``, ``SyscallResult``, ``EvaluationResult``,
    ``ProgressDelta``, and ``LoopDecision`` contracts so an ALI
    session can consume an :class:`AgentCommandResult` directly.
    """

    model_config = ConfigDict(extra="forbid")

    command_id: str
    goal_id: str
    status: AgentCommandStatus
    success: bool = False
    policy_decision: PolicyDecision
    observation: ObservationSummary = Field(default_factory=ObservationSummary)
    evaluation: EvaluationHint = Field(default_factory=EvaluationHint)
    progress: ProgressSnapshot = Field(default_factory=ProgressSnapshot)
    convergence: ConvergenceSnapshot = Field(default_factory=ConvergenceSnapshot)
    trace_id: str | None = None
    blocked_reason: str | None = None
    requires_approval: bool = False
    dry_run: bool = False
    created_at: datetime = Field(default_factory=_utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("status")
    @classmethod
    def status_consistent(cls, value: AgentCommandStatus) -> AgentCommandStatus:
        return value

    def to_json(self) -> str:
        return self.model_dump_json(exclude_none=True)

    @classmethod
    def from_json(cls, raw: str | bytes | dict[str, Any]) -> "AgentCommandResult":
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        if isinstance(raw, str):
            data = json.loads(raw)
        else:
            data = raw
        return cls.model_validate(data)


def parse_command(raw: str | dict[str, Any]) -> AgentCommand:
    """Parse a JSON string or mapping into an :class:`AgentCommand`."""

    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            from loopos.aci.errors import CommandValidationError

            raise CommandValidationError(f"command is not valid JSON: {exc}") from exc
    else:
        data = raw
    return AgentCommand.model_validate(data)


def serialize_command(command: AgentCommand) -> str:
    """Return a stable JSON representation of an :class:`AgentCommand`."""

    return command.model_dump_json(exclude_none=True)
