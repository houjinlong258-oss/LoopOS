"""Typed models for the Agent Loop Interface FSM and session.

The states and events defined here are the canonical ALI surface.
They map 1:1 to the convergence and scheduler decisions already
exposed by the v0.1 runtime, so a Phase 1+ loop engine can speak ALI
without rewriting the existing semantics.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---- States -------------------------------------------------------------

AgentLoopState = Literal[
    "CREATED",
    "READY",
    "RUNNING",
    "WAITING_APPROVAL",
    "REPAIRING",
    "REPLANNING",
    "ASKING_USER",
    "HALTED_SUCCESS",
    "HALTED_FAILURE",
    "HALTED_BLOCKED",
]

TERMINAL_STATES: frozenset[AgentLoopState] = frozenset(
    {"HALTED_SUCCESS", "HALTED_FAILURE", "HALTED_BLOCKED"}
)

# ---- Events -------------------------------------------------------------

AgentLoopEvent = Literal[
    "goal_submitted",
    "command_submitted",
    "policy_allowed",
    "policy_denied",
    "approval_required",
    "syscall_completed",
    "syscall_failed",
    "observation_recorded",
    "evaluation_applied",
    "progress_updated",
    "convergence_continue",
    "convergence_repair",
    "convergence_replan",
    "convergence_ask",
    "convergence_halt_success",
    "convergence_halt_failure",
    "convergence_halt_blocked",
]

# Convergence signals. ALI uses them to express the convergence
# contract without depending on the v0.1 Convergence module.
ConvergenceSignal = Literal[
    "continue",
    "repair",
    "replan",
    "ask_user",
    "wait_approval",
    "halt_success",
    "halt_failure",
    "halt_blocked",
]

CONVERGENCE_EVENTS: dict[ConvergenceSignal, AgentLoopEvent] = {
    "continue": "convergence_continue",
    "repair": "convergence_repair",
    "replan": "convergence_replan",
    "ask_user": "convergence_ask",
    "wait_approval": "approval_required",
    "halt_success": "convergence_halt_success",
    "halt_failure": "convergence_halt_failure",
    "halt_blocked": "convergence_halt_blocked",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ---- Transition row -----------------------------------------------------


class TransitionRow(BaseModel):
    """A single (state, event) -> next-state row in the FSM table.

    The :class:`loopos.ali.fsm.AgentLoopFSM` builds a transition table
    out of :class:`TransitionRow` instances and consults it on every
    event. The table itself is data, not a maze of ``if`` statements.
    """

    model_config = ConfigDict(extra="forbid")

    state: AgentLoopState
    event: AgentLoopEvent
    next_state: AgentLoopState
    reason_code: str
    requires_payload_keys: tuple[str, ...] = ()

    @field_validator("state", "event", "next_state", "reason_code")
    @classmethod
    def non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value


# ---- Session ------------------------------------------------------------


class _ACIResultRef(BaseModel):
    """Reference to an :class:`loopos.aci.AgentCommandResult`.

    The session keeps a compact reference instead of importing or
    copying the full ACI result. A consumer can re-fetch the full
    payload through ``aci_result_id`` if needed.
    """

    model_config = ConfigDict(extra="forbid")

    aci_result_id: str
    status: str
    success: bool
    goal_id: str
    blocked_reason: str | None = None
    requires_approval: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentLoopEventRecord(BaseModel):
    """An event applied to a session, kept for replay and audit."""

    model_config = ConfigDict(extra="forbid")

    seq: int = Field(ge=0)
    event: AgentLoopEvent
    payload: dict[str, Any] = Field(default_factory=dict)
    reason_code: str
    next_state: AgentLoopState
    created_at: datetime = Field(default_factory=_utc_now)


class AgentLoopSession(BaseModel):
    """A bounded, replayable ALI session for one LoopOS run."""

    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(default_factory=lambda: str(uuid4()))
    goal_id: str
    state: AgentLoopState = "CREATED"
    max_events: int = Field(default=1024, ge=1, le=65536)
    events: list[AgentLoopEventRecord] = Field(default_factory=list)
    aci_refs: list[_ACIResultRef] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("goal_id")
    @classmethod
    def goal_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("goal_id is required")
        return value

    @model_validator(mode="after")
    def _enforce_event_cap(self) -> "AgentLoopSession":
        if len(self.events) > self.max_events:
            raise ValueError(f"session exceeded max_events={self.max_events}")
        return self

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    @property
    def event_count(self) -> int:
        return len(self.events)

    def attach_aci_result(
        self,
        *,
        aci_result_id: str,
        status: str,
        success: bool,
        goal_id: str,
        blocked_reason: str | None = None,
        requires_approval: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Attach an ACI result reference to this session.

        The reference is intentionally a thin pointer, not a copy.
        Importing the full :class:`AgentCommandResult` is the
        consumer's responsibility so the ALI package does not
        transitively import the ACI package.
        """

        self.aci_refs.append(
            _ACIResultRef(
                aci_result_id=aci_result_id,
                status=status,
                success=success,
                goal_id=goal_id,
                blocked_reason=blocked_reason,
                requires_approval=requires_approval,
                metadata=metadata or {},
            )
        )
        self.updated_at = _utc_now()

    def latest_aci_ref(self) -> _ACIResultRef | None:
        if not self.aci_refs:
            return None
        return self.aci_refs[-1]
