"""Bridge between ALI events and the LoopOS trace runtime.

This module persists :class:`AgentLoopEventRecord` values into the
existing :class:`loopos.kernel.trace.TraceStore`. The bridge is a
thin wrapper: it does not replace or extend the trace runtime; it
only translates ALI-side event records into the
:class:`loopos.kernel.trace.TraceEvent` shape that the runtime
already accepts.

Design constraints:

* The trace runtime (``TraceStore`` / ``TraceEvent``) is the single
  source of truth for trace evidence. The bridge does not introduce
  a new store, a new wire format, or a new event type.
* Each ALI event becomes a trace event of kind ``"signal"`` with
  ``event_type="ali.event"``. The ``payload`` carries the full
  event record (seq, event, reason_code, next_state, payload,
  created_at) plus the audit-trail fields the kernel already
  maintains (command_id, goal_id, trace_id, syscall_id,
  provider_id, reason_codes, policy_decision summary).
* The bridge is deterministic: given the same list of records,
  it appends trace events with identical ``payload`` keys. Replay
  reconstructs the ordered ALI event stream by reading the trace
  store and filtering on ``event_type="ali.event"``.
* Dry-run ACI results are traceable (the bridge emits events) but
  the events are observation-only; they never cause
  filesystem / provider / syscall side effects.

Public surface:

* :func:`persist_session_events` -- persist a session's event
  records to a trace store.
* :func:`replay_session_events` -- read the persisted trace events
  back as ordered :class:`AgentLoopEventRecord` shapes.
* :data:`ALI_EVENT_TYPE` -- the discriminator used as the
  ``event_type`` argument to ``TraceStore.append``.
"""

from __future__ import annotations

from typing import Any

from loopos.ali.models import (
    AgentLoopEventRecord,
    AgentLoopSession,
)
from loopos.kernel.trace import TraceEvent, TraceStore

# Discriminator for ALI events inside the trace store. Stored in
# ``TraceEvent.event_type`` so legacy consumers can filter without
# parsing the payload.
ALI_EVENT_TYPE: str = "ali.event"

# Stable payload key order. The bridge writes the same keys in the
# same order on every call so trace replay is deterministic.
_PAYLOAD_KEY_ORDER: tuple[str, ...] = (
    "seq",
    "event",
    "reason_code",
    "next_state",
    "created_at",
    "aci_command_id",
    "aci_goal_id",
    "aci_status",
    "aci_success",
    "reason_codes",
    "messages",
    "trace_id",
    "syscall_id",
    "provider_id",
    "provider_source",
    "policy_decision",
    "convergence_reason_code",
)


def _ordered_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a new dict whose keys appear in :data:`_PAYLOAD_KEY_ORDER`.

    Extra keys (e.g. from a future ALI event) are appended in
    alphabetical order so the JSON serialisation stays stable.
    """

    ordered: dict[str, Any] = {}
    for key in _PAYLOAD_KEY_ORDER:
        if key in payload:
            ordered[key] = payload[key]
    extras = sorted(k for k in payload if k not in ordered)
    for key in extras:
        ordered[key] = payload[key]
    return ordered


def _record_to_payload(
    record: AgentLoopEventRecord,
    *,
    audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Translate one :class:`AgentLoopEventRecord` into a trace payload.

    The audit metadata (command_id, trace_id, syscall_id, ...) is
    sourced from the caller-provided audit dict, which mirrors the
    metadata :func:`consume_aci_result` attaches to the event's
    payload via :meth:`AgentLoopSession.attach_aci_result`.
    """

    payload: dict[str, Any] = {
        "seq": record.seq,
        "event": record.event,
        "reason_code": record.reason_code,
        "next_state": record.next_state,
        "created_at": record.created_at.isoformat(),
    }
    if audit:
        for key, value in audit.items():
            payload[key] = value
    # Surface the structured event payload fields at the top level
    # so the trace consumer can read them without descending into
    # a nested object. ``command_id`` / ``goal_id`` are already in
    # the audit dict when the bridge is wired via the kernel hook.
    return _ordered_payload(payload)


def persist_session_events(
    session: AgentLoopSession,
    *,
    run_id: str,
    step: int,
    trace_store: TraceStore,
    audit: dict[str, Any] | None = None,
    records: list[AgentLoopEventRecord] | None = None,
) -> list[TraceEvent]:
    """Persist ALI event records to a trace store.

    Parameters
    ----------
    session:
        The :class:`AgentLoopSession` whose events to persist.
        The session itself is not stored; only the records it
        contains.
    run_id:
        The kernel run id that owns this session. Required by the
        :class:`TraceEvent` schema.
    step:
        The current kernel step. Persisted on every trace event so
        trace consumers can correlate ALI events with the kernel
        decision trace.
    trace_store:
        The destination trace store.
    audit:
        Optional structured audit metadata merged into every
        payload. The kernel hook passes
        ``run.metadata['aci_outcomes'][-1]`` here so the trace
        events carry command_id / goal_id / trace_id / syscall_id
        / provider_id / reason_codes / policy_decision summary /
        convergence_reason_code without re-running the policy
        engine.
    records:
        Optional explicit list of records to persist. When
        ``None``, the bridge persists ``session.events``. The
        kernel hook passes the records returned by
        :func:`consume_aci_result` so only the new events are
        persisted on each call.

    Returns
    -------
    list[:class:`TraceEvent`]
        The trace events that were appended, in order.
    """

    target = records if records is not None else list(session.events)
    events: list[TraceEvent] = []
    for record in target:
        payload = _record_to_payload(record, audit=audit)
        event = trace_store.append(
            "signal",
            run_id=run_id,
            step=step,
            payload=payload,
            event_type=ALI_EVENT_TYPE,
            syscall_id=payload.get("syscall_id") if isinstance(payload.get("syscall_id"), str) else None,
        )
        events.append(event)
    return events


def replay_session_events(
    trace_store: TraceStore,
    *,
    run_id: str,
) -> list[dict[str, Any]]:
    """Read persisted ALI events back as an ordered stream.

    Filters the trace store on ``event_type="ali.event"`` and
    returns the records in append order. The returned dicts match
    the shape :func:`loopos.ali.session.to_event_stream` produces
    (plus the audit fields), so a replay consumer can rebuild an
    :class:`AgentLoopSession` from scratch.
    """

    records: list[dict[str, Any]] = []
    for event in trace_store.list(run_id=run_id):
        # ``TraceEvent`` exposes the legacy ``type`` field (not
        # ``event_type``); the bridge writes ``ALI_EVENT_TYPE``
        # there for discriminator filtering on replay.
        if event.type != ALI_EVENT_TYPE:
            continue
        records.append(_ordered_payload(dict(event.payload)))
    records.sort(key=lambda item: item.get("seq", 0))
    return records


__all__ = [
    "ALI_EVENT_TYPE",
    "persist_session_events",
    "replay_session_events",
]