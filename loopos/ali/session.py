"""Session helpers for the Agent Loop Interface.

A session is a thin owner of an :class:`AgentLoopFSM` plus a typed
:func:`apply_event` convenience. The session can serialize itself
through Pydantic, can reference an :class:`AgentCommandResult` without
importing the ACI package's full surface (only :mod:`loopos.aci.models`
is pulled in for the typed ``consume_aci_result`` consumer), and has
no side effects beyond mutating its own state.

Phase 3 adds :func:`consume_aci_result`, which maps an
:class:`loopos.aci.AgentCommandResult` to a sequence of
:class:`AgentLoopEvent` values and drives the existing FSM through
them. The mapping is data-only and the FSM transition table stays
the single source of truth for state transitions.

The session does not reach into the loop kernel subsystem or its
loop engine class; those live in a separate package that ALI
consumers (the v0.1 kernel loop engine first, then later phases)
import on their own. Kernel integration is a Phase 4+ follow-up.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loopos.aci.models import AgentCommandResult
from loopos.ali.errors import (
    InvalidTransitionError,
    SessionClosedError,
    UnknownEventError,
)
from loopos.ali.fsm import AgentLoopFSM, DEFAULT_FSM
from loopos.ali.models import (
    AgentLoopEvent,
    AgentLoopEventRecord,
    AgentLoopSession,
)


@dataclass(frozen=True)
class SessionConfig:
    """Configuration for :func:`create_session`.

    The config is intentionally small. The session does not own a
    workspace, a router, or a runtime; it owns FSM state and the
    audit history.
    """

    max_events: int = 1024


def create_session(
    goal_id: str,
    *,
    fsm: AgentLoopFSM | None = None,
    config: SessionConfig | None = None,
) -> AgentLoopSession:
    """Create a new :class:`AgentLoopSession` bound to a goal id."""

    session = AgentLoopSession(
        goal_id=goal_id,
        max_events=config.max_events if config else 1024,
    )
    session.metadata["fsm_table_size"] = len((fsm or DEFAULT_FSM).table)
    return session


def apply_event(
    session: AgentLoopSession,
    event: AgentLoopEvent,
    payload: dict[str, Any] | None = None,
    *,
    fsm: AgentLoopFSM | None = None,
) -> AgentLoopEventRecord:
    """Apply an event to a session through the supplied or default FSM.

    The helper exists so callers do not have to import
    :class:`AgentLoopFSM` directly when they only want to advance a
    session. The underlying FSM is the source of truth; this function
    is a thin pass-through with clearer naming.
    """

    engine = fsm or DEFAULT_FSM
    try:
        return engine.apply(session, event, payload)
    except (InvalidTransitionError, UnknownEventError):
        raise


# ---------------------------------------------------------------------------
# Phase 3: ACI result consumption
# ---------------------------------------------------------------------------

# Reason codes that the runner emits when Policy OS denies a command.
# When any of these appears in an :class:`AgentCommandResult.reason_codes`,
# the consumption treats the blocked result as a policy denial rather
# than a structural / validation block.
_POLICY_DENIAL_REASONS: frozenset[str] = frozenset(
    {
        "policy_denied",
        "terminal_rm_rf_denied",
        "remote_script_pipe_denied",
        "network_access_denied",
        "git_tag_denied",
        "release_evidence_mutation_denied",
    }
)


def _extract_event_payload(result: AgentCommandResult) -> dict[str, Any]:
    """Build a structured event payload from an ACI result.

    The payload is the contract the rest of LoopOS reads off the
    ALI event record. It carries the audit trail (command_id,
    goal_id, trace_id, syscall_id, provider_id) so downstream
    consumers (Review artifact, Readiness proof) do not need to
    re-resolve anything.
    """

    payload: dict[str, Any] = {
        "command_id": result.command_id,
        "goal_id": result.goal_id,
        "aci_status": result.status,
        "aci_success": result.success,
        "reason_codes": list(result.reason_codes),
        "messages": list(result.messages),
    }
    if result.trace_id:
        payload["trace_id"] = result.trace_id
    syscall_id = result.metadata.get("syscall_id")
    if isinstance(syscall_id, str) and syscall_id:
        payload["syscall_id"] = syscall_id
    if result.resolved_provider is not None:
        payload["provider_id"] = result.resolved_provider.provider_id
        payload["provider_source"] = result.resolved_provider.source
    pds = result.policy_decision_summary
    if pds is not None:
        payload["policy_decision"] = {
            "decision_id": pds.decision_id,
            "allowed": pds.allowed,
            "action": pds.action,
            "safety_level": pds.safety_level,
            "reason_codes": list(pds.reason_codes),
        }
    if result.convergence.reason_code:
        payload["convergence_reason_code"] = result.convergence.reason_code
    return payload


def _is_policy_denial(result: AgentCommandResult) -> bool:
    """True when the result's denial came from Policy OS, not validation.

    The runner writes a distinct set of reason codes for policy
    denials; structural / validation blocks carry different codes.
    Falling back to ``policy_decision_summary.allowed=False``
    keeps the check robust when a caller constructs an
    :class:`AgentCommandResult` manually.
    """

    if result.policy_decision_summary is not None and not result.policy_decision_summary.allowed:
        return True
    if set(result.reason_codes) & _POLICY_DENIAL_REASONS:
        return True
    return False


def _desired_event_sequence(result: AgentCommandResult) -> list[AgentLoopEvent]:
    """Map an :class:`AgentCommandResult` to the canonical event sequence.

    This is the *desired* sequence assuming the session is in
    ``RUNNING``. The actual emission is filtered against the FSM's
    transition table in :func:`_filter_for_state` so that the consumer
    remains state-aware.
    """

    if result.status == "completed":
        # Dry-run success is reported as ``completed`` with
        # ``dry_run=True``. We emit ``progress_updated`` but not
        # ``syscall_completed`` because no side-effecting syscall ran.
        if result.dry_run:
            return ["progress_updated"]
        return ["progress_updated", "syscall_completed"]

    if result.status == "dry_run":
        return ["progress_updated"]

    if result.status == "approval_required":
        return ["approval_required"]

    if result.status == "blocked":
        if _is_policy_denial(result):
            return ["policy_denied"]
        return ["convergence_halt_blocked"]

    if result.status == "unsupported":
        # Per the Phase 2 contract, ``unsupported`` is reserved for
        # kinds whose schema value exists but whose execution path
        # has not landed yet (e.g. ``file.patch``). The agent cannot
        # repair this on its own -- it must replan with a different
        # kind -- so the safe default is a halt with the
        # ``unsupported_command_kind`` reason code preserved.
        return ["convergence_halt_failure"]

    if result.status == "failed":
        # Distinguish repairable, replan-needed, and non-repairable
        # failures. The runner surfaces repair hints via
        # ``EvaluationSummary.repairable`` and no-progress hints via
        # ``ProgressSummary.no_progress``; both are placeholder fields
        # populated by the kernel runtime in a future phase, but the
        # consumption logic reads them now so the contract is pinned.
        if result.evaluation.repairable:
            return ["progress_updated", "syscall_failed"]
        if result.progress.no_progress:
            return ["progress_updated", "convergence_replan"]
        return ["progress_updated", "convergence_halt_failure"]

    # Unknown / future status: fail closed.
    return ["progress_updated", "convergence_halt_failure"]


def _valid_events_in_state(
    state: str,
    *,
    fsm: AgentLoopFSM | None = None,
) -> frozenset[str]:
    """Return the set of events the FSM accepts from ``state``.

    The FSM table is the single source of truth for valid
    transitions; the consumer does not maintain a parallel copy.
    """

    engine = fsm or DEFAULT_FSM
    return frozenset(row.event for row in engine.table if row.state == state)


def _filter_for_state(
    desired: list[AgentLoopEvent],
    current_state: str,
    *,
    fsm: AgentLoopFSM | None = None,
) -> list[AgentLoopEvent]:
    """Drop events that are not valid from ``current_state``.

    The consumer emits the desired sequence in order. ``progress_updated``
    is only valid from ``RUNNING``; ``syscall_completed`` is also only
    valid from ``RUNNING``; ``policy_denied`` is valid from
    ``RUNNING`` and ``WAITING_APPROVAL``. By filtering against the
    FSM table we stay consistent with the transition table without
    duplicating state-machine knowledge in this module.

    If the filtered sequence becomes empty, the caller has driven
    the session into a state from which no event in the desired
    sequence is valid. :func:`consume_aci_result` raises
    :class:`InvalidTransitionError` in that case.
    """

    valid = _valid_events_in_state(current_state, fsm=fsm)
    return [event for event in desired if event in valid]


def consume_aci_result(
    session: AgentLoopSession,
    result: AgentCommandResult,
    *,
    fsm: AgentLoopFSM | None = None,
) -> list[AgentLoopEventRecord]:
    """Consume an :class:`AgentCommandResult` and drive the FSM.

    Phase 3 ALI consumption contract:

    1. Reject terminal sessions with :class:`SessionClosedError`.
    2. Attach the ACI result as an audit reference via
       :meth:`AgentLoopSession.attach_aci_result` (preserves the
       ``command_id``, ``status``, ``success``, ``reason_codes``,
       ``trace_id``, ``provider_id``, ``syscall_id``).
    3. Compute the desired event sequence from the result's status,
       ``success`` flag, ``reason_codes``, ``evaluation`` and
       ``progress`` placeholders.
    4. Filter the sequence against the FSM's transition table so
       events that are not valid from the current state are
       dropped. ``progress_updated`` is dropped in REPAIRING /
       REPLANNING, for example, so a failed-result from those
       states emits only ``syscall_failed``.
    5. Apply each remaining event through :func:`apply_event` so
       the existing transition table stays the single source of
       truth for state transitions.

    The function never raises on a well-formed :class:`AgentCommandResult`;
    the only ways it can fail are:

    * the session is in a terminal state (rejected up front);
    * no event in the desired sequence is valid from the current
      state (propagated as :class:`InvalidTransitionError`).

    Pre-conditions:

    * The session must not be in a terminal state. The caller is
      expected to advance the session through ``goal_submitted`` and
      ``command_submitted`` (or an equivalent path) before invoking
      this helper.
    * The session must be in a state from which at least one event
      in the desired sequence is valid. Typical valid states are
      ``RUNNING``, ``REPAIRING``, ``REPLANNING``, ``WAITING_APPROVAL``.
    """

    if session.is_terminal:
        raise SessionClosedError(
            f"cannot consume ACI result in terminal state: {session.state!r}"
        )

    # 1. Attach the audit reference first so a downstream consumer
    #    can always look up the result even if the FSM transition
    #    raises mid-sequence (we do not swallow the FSM error; the
    #    caller catches it and the partial attachment remains).
    session.attach_aci_result(
        aci_result_id=result.command_id,
        status=result.status,
        success=result.success,
        goal_id=result.goal_id,
        blocked_reason=result.blocked_reason,
        requires_approval=result.requires_approval,
        metadata={
            "reason_codes": list(result.reason_codes),
            "trace_id": result.trace_id,
            "provider_id": (
                result.resolved_provider.provider_id
                if result.resolved_provider is not None
                else None
            ),
        },
    )

    # 2. Compute the desired sequence and filter against the FSM.
    desired = _desired_event_sequence(result)
    events = _filter_for_state(desired, session.state, fsm=fsm)
    if not events:
        raise InvalidTransitionError(
            f"no valid event in state={session.state!r} for "
            f"aci_status={result.status!r}; transition table rejects "
            f"desired sequence {desired!r}"
        )

    payload = _extract_event_payload(result)
    records: list[AgentLoopEventRecord] = []
    for event in events:
        record = apply_event(session, event, payload, fsm=fsm)
        records.append(record)
    return records
