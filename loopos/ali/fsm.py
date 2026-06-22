"""Transition-table driven ALI finite-state machine.

The FSM is the only authority on which state an event moves the
session to. The transition table is data, not a maze of ``if``
branches, so new states and events can be added by appending rows
without rewriting the engine.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from loopos.ali.errors import (
    InvalidTransitionError,
    SessionClosedError,
    UnknownEventError,
)
from loopos.ali.models import (
    AgentLoopEvent,
    AgentLoopEventRecord,
    AgentLoopSession,
    AgentLoopState,
    TransitionRow,
)

# ---- Transition table ---------------------------------------------------

# Each row is (state, event) -> (next_state, reason_code, payload keys).
# The keys, when non-empty, are required in the event payload.
TABLE: tuple[TransitionRow, ...] = (
    # --- Boot and submit ---
    TransitionRow(
        state="CREATED",
        event="goal_submitted",
        next_state="READY",
        reason_code="ali.goal_submitted",
    ),
    TransitionRow(
        state="READY",
        event="command_submitted",
        next_state="RUNNING",
        reason_code="ali.command_submitted",
    ),
    # --- Policy outcomes ---
    TransitionRow(
        state="RUNNING",
        event="policy_allowed",
        next_state="RUNNING",
        reason_code="ali.policy_allowed",
    ),
    TransitionRow(
        state="RUNNING",
        event="policy_denied",
        next_state="HALTED_BLOCKED",
        reason_code="ali.policy_denied",
    ),
    TransitionRow(
        state="RUNNING",
        event="approval_required",
        next_state="WAITING_APPROVAL",
        reason_code="ali.approval_required",
    ),
    TransitionRow(
        state="WAITING_APPROVAL",
        event="policy_allowed",
        next_state="RUNNING",
        reason_code="ali.approval_granted",
    ),
    TransitionRow(
        state="WAITING_APPROVAL",
        event="policy_denied",
        next_state="HALTED_BLOCKED",
        reason_code="ali.approval_denied",
    ),
    # --- Syscall outcomes ---
    TransitionRow(
        state="RUNNING",
        event="syscall_completed",
        next_state="RUNNING",
        reason_code="ali.syscall_completed",
    ),
    TransitionRow(
        state="RUNNING",
        event="syscall_failed",
        next_state="REPAIRING",
        reason_code="ali.syscall_failed_repairable",
    ),
    TransitionRow(
        state="RUNNING",
        event="observation_recorded",
        next_state="RUNNING",
        reason_code="ali.observation_recorded",
    ),
    # --- Evaluation / progress ---
    TransitionRow(
        state="RUNNING",
        event="evaluation_applied",
        next_state="RUNNING",
        reason_code="ali.evaluation_applied",
    ),
    TransitionRow(
        state="RUNNING",
        event="progress_updated",
        next_state="RUNNING",
        reason_code="ali.progress_updated",
    ),
    # --- Repair / replan / ask ---
    TransitionRow(
        state="REPAIRING",
        event="command_submitted",
        next_state="RUNNING",
        reason_code="ali.repair_command_submitted",
    ),
    TransitionRow(
        state="REPAIRING",
        event="syscall_failed",
        next_state="REPLANNING",
        reason_code="ali.repair_repeated_failure",
    ),
    TransitionRow(
        state="RUNNING",
        event="convergence_replan",
        next_state="REPLANNING",
        reason_code="ali.convergence_replan",
    ),
    TransitionRow(
        state="REPAIRING",
        event="convergence_replan",
        next_state="REPLANNING",
        reason_code="ali.repair_to_replan",
    ),
    TransitionRow(
        state="REPLANNING",
        event="command_submitted",
        next_state="RUNNING",
        reason_code="ali.replan_command_submitted",
    ),
    TransitionRow(
        state="RUNNING",
        event="convergence_ask",
        next_state="ASKING_USER",
        reason_code="ali.convergence_ask",
    ),
    TransitionRow(
        state="REPAIRING",
        event="convergence_ask",
        next_state="ASKING_USER",
        reason_code="ali.repair_to_ask",
    ),
    TransitionRow(
        state="ASKING_USER",
        event="command_submitted",
        next_state="RUNNING",
        reason_code="ali.user_response_received",
    ),
    # --- Continue ---
    TransitionRow(
        state="RUNNING",
        event="convergence_continue",
        next_state="RUNNING",
        reason_code="ali.convergence_continue",
    ),
    # --- Halt ---
    TransitionRow(
        state="RUNNING",
        event="convergence_halt_success",
        next_state="HALTED_SUCCESS",
        reason_code="ali.halt_success",
    ),
    TransitionRow(
        state="REPAIRING",
        event="convergence_halt_success",
        next_state="HALTED_SUCCESS",
        reason_code="ali.halt_success",
    ),
    TransitionRow(
        state="REPLANNING",
        event="convergence_halt_success",
        next_state="HALTED_SUCCESS",
        reason_code="ali.halt_success",
    ),
    TransitionRow(
        state="ASKING_USER",
        event="convergence_halt_success",
        next_state="HALTED_SUCCESS",
        reason_code="ali.halt_success",
    ),
    TransitionRow(
        state="WAITING_APPROVAL",
        event="convergence_halt_success",
        next_state="HALTED_SUCCESS",
        reason_code="ali.halt_success",
    ),
    TransitionRow(
        state="RUNNING",
        event="convergence_halt_failure",
        next_state="HALTED_FAILURE",
        reason_code="ali.halt_failure",
    ),
    TransitionRow(
        state="REPAIRING",
        event="convergence_halt_failure",
        next_state="HALTED_FAILURE",
        reason_code="ali.halt_failure",
    ),
    TransitionRow(
        state="REPLANNING",
        event="convergence_halt_failure",
        next_state="HALTED_FAILURE",
        reason_code="ali.halt_failure",
    ),
    TransitionRow(
        state="ASKING_USER",
        event="convergence_halt_failure",
        next_state="HALTED_FAILURE",
        reason_code="ali.halt_failure",
    ),
    TransitionRow(
        state="WAITING_APPROVAL",
        event="convergence_halt_failure",
        next_state="HALTED_FAILURE",
        reason_code="ali.halt_failure",
    ),
    TransitionRow(
        state="RUNNING",
        event="convergence_halt_blocked",
        next_state="HALTED_BLOCKED",
        reason_code="ali.halt_blocked",
    ),
    TransitionRow(
        state="REPAIRING",
        event="convergence_halt_blocked",
        next_state="HALTED_BLOCKED",
        reason_code="ali.halt_blocked",
    ),
    TransitionRow(
        state="REPLANNING",
        event="convergence_halt_blocked",
        next_state="HALTED_BLOCKED",
        reason_code="ali.halt_blocked",
    ),
    TransitionRow(
        state="ASKING_USER",
        event="convergence_halt_blocked",
        next_state="HALTED_BLOCKED",
        reason_code="ali.halt_blocked",
    ),
    TransitionRow(
        state="WAITING_APPROVAL",
        event="convergence_halt_blocked",
        next_state="HALTED_BLOCKED",
        reason_code="ali.halt_blocked",
    ),
)


_VALID_STATES: frozenset[AgentLoopState] = frozenset(
    {
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
    }
)
_VALID_EVENTS: frozenset[AgentLoopEvent] = frozenset(row.event for row in TABLE)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ---- Engine -------------------------------------------------------------


class AgentLoopFSM:
    """Transition-table driven ALI finite-state machine.

    The engine holds the transition table as a list of
    :class:`TransitionRow` and uses a small dispatch helper. It does
    **not** import ``loopos.kernel.*`` and does not touch
    ``KernelLoopEngine``.
    """

    def __init__(self, table: Iterable[TransitionRow] | None = None) -> None:
        self._table: list[TransitionRow] = list(table) if table is not None else list(TABLE)
        self._index: dict[tuple[AgentLoopState, AgentLoopEvent], TransitionRow] = {
            (row.state, row.event): row for row in self._table
        }

    @property
    def table(self) -> tuple[TransitionRow, ...]:
        return tuple(self._table)

    def lookup(self, state: AgentLoopState, event: AgentLoopEvent) -> TransitionRow | None:
        return self._index.get((state, event))

    def valid_events(self, state: AgentLoopState) -> tuple[AgentLoopEvent, ...]:
        return tuple(row.event for row in self._table if row.state == state)

    def apply(
        self,
        session: AgentLoopSession,
        event: AgentLoopEvent,
        payload: dict[str, Any] | None = None,
    ) -> AgentLoopEventRecord:
        """Apply an event to a session and return the audit record."""

        if event not in _VALID_EVENTS:
            raise UnknownEventError(f"unknown ALI event: {event!r}")
        if session.is_terminal:
            raise SessionClosedError(
                f"cannot apply {event!r}: session is halted in {session.state!r}"
            )
        row = self._index.get((session.state, event))
        if row is None:
            raise InvalidTransitionError(
                f"no transition for state={session.state!r} event={event!r}"
            )
        merged = dict(payload or {})
        missing = [k for k in row.requires_payload_keys if k not in merged]
        if missing:
            raise InvalidTransitionError(
                f"event {event!r} requires payload keys: {', '.join(missing)}"
            )
        seq = session.event_count
        record = AgentLoopEventRecord(
            seq=seq,
            event=event,
            payload=merged,
            reason_code=row.reason_code,
            next_state=row.next_state,
        )
        session.events.append(record)
        session.state = row.next_state
        session.updated_at = _utc_now()
        return record

    @staticmethod
    def is_valid_state(state: str) -> bool:
        return state in _VALID_STATES


# Re-export a single immutable default engine for read-only callers.
DEFAULT_FSM = AgentLoopFSM()


__all__ = ["AgentLoopFSM", "TransitionRow", "DEFAULT_FSM"]
