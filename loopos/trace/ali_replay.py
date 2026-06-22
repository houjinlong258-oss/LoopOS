"""ALI Replay Engine.

The replay engine is the v0.2 deep-smoke / readiness-proof surface
that proves ALI event sequences are **deterministic and
replayable**. It does not introduce a new store, a new event type,
or a new wire format; it reads :class:`AgentLoopEventRecord`
values from the existing :class:`TraceStore` (filtering on
``event_type='ali.event'``) and rebuilds a fresh
:class:`AgentLoopSession` by replaying each event through the
existing :class:`AgentLoopFSM`.

Design constraints (master prompt, Phase 8):

* Do not re-run ACI.
* Do not re-run Policy OS.
* Do not re-run Syscall Router.
* Do not call providers.
* Do not run subprocess.
* Same ordered event stream -> same final session state.

Public surface:

* :func:`replay_session_from_trace` -- rebuild a session from
  the trace store.
* :func:`replay_events` -- replay a pre-ordered list of
  :class:`AgentLoopEventRecord`-shaped dicts.
* :dataclass:`ReplayResult` -- the structured replay outcome.

The engine is intentionally small: it is the deterministic
replay proof surface that ``docs/v0-2-readiness.md`` documents,
not a runtime path. Callers that want to inspect the trace
runtime directly should keep using
:func:`loopos.trace.ali_bridge.replay_session_events`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

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
    TERMINAL_STATES,
)
from loopos.ali.session import create_session
from loopos.kernel.trace import TraceEvent, TraceStore
from loopos.trace.ali_bridge import ALI_EVENT_TYPE


# Sentinel markers. The replay engine is pure: no network, no
# subprocess, no provider API, no Policy OS call, no Syscall
# Router invocation. Anything in the event stream that would
# require a side-effecting call is dropped with a deterministic
# note on the result.
_ALLOWED_EVENT_VALUES: frozenset[str] = frozenset(AgentLoopEvent.__args__)  # type: ignore[attr-defined]


@dataclass
class ReplayResult:
    """Structured outcome of a replay run.

    Attributes
    ----------
    session:
        The rebuilt :class:`AgentLoopSession`. Always present,
        even when the replay encountered deterministic deviations
        (so callers can still inspect the final state).
    expected_event_count:
        Number of events fed to the replay.
    replayed_event_count:
        Number of events successfully re-applied.
    dropped_events:
        Ordered list of ``(seq, event, reason)`` tuples for events
        that could not be replayed. The reasons are stable strings:
        ``"unknown_event"``, ``"invalid_transition"``,
        ``"session_closed"``, ``"post_terminal"``.
    final_state:
        Convenience for ``session.state``.
    halted:
        ``True`` when the session ended in a ``TERMINAL_STATES``
        member.
    """

    session: AgentLoopSession
    expected_event_count: int
    replayed_event_count: int
    dropped_events: list[tuple[int, str, str]] = field(default_factory=list)
    final_state: str = ""
    halted: bool = False


def _coerce_record(item: dict[str, Any]) -> AgentLoopEventRecord:
    """Coerce a trace payload dict into an :class:`AgentLoopEventRecord`.

    The bridge writes canonical payload keys (``seq``, ``event``,
    ``reason_code``, ``next_state``, ``created_at``) plus the audit
    keys. The replay engine only needs the typed shape; extra keys
    are preserved in ``payload``.
    """

    event = item.get("event")
    if not isinstance(event, str) or event not in _ALLOWED_EVENT_VALUES:
        raise UnknownEventError(f"unknown ALI event: {event!r}")
    seq_raw = item.get("seq", 0)
    try:
        seq = int(seq_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid seq: {seq_raw!r}") from exc
    payload = dict(item)
    # Strip the typed fields so they go through Pydantic, not nested.
    for key in ("seq", "event", "reason_code", "next_state"):
        payload.pop(key, None)
    return AgentLoopEventRecord(
        seq=seq,
        event=event,  # type: ignore[arg-type]
        payload=payload,
        reason_code=str(item.get("reason_code", "")),
        next_state=str(item.get("next_state", "CREATED")),
    )


def _ordered_records(
    trace_store: TraceStore,
    *,
    run_id: str,
) -> list[AgentLoopEventRecord]:
    """Read ``ali.event`` records from ``trace_store`` for ``run_id``.

    Filters on the legacy ``type`` discriminator the bridge writes
    (the bridge sets ``type=ALI_EVENT_TYPE``). Returns the records
    in stable ``seq`` order.
    """

    raw: list[dict[str, Any]] = []
    for event in trace_store.list(run_id=run_id):
        # ``TraceEvent`` exposes the legacy ``type`` field (not
        # ``event_type``); the bridge writes ``ALI_EVENT_TYPE``
        # there for discriminator filtering on replay.
        if event.type != ALI_EVENT_TYPE:
            continue
        raw.append(dict(event.payload))
    raw.sort(key=lambda item: int(item.get("seq", 0)))
    return [_coerce_record(item) for item in raw]


def replay_events(
    events: Sequence[dict[str, Any] | AgentLoopEventRecord],
    *,
    goal_id: str = "replay-goal",
    fsm: AgentLoopFSM | None = None,
) -> ReplayResult:
    """Replay an ordered list of events through the ALI FSM.

    Parameters
    ----------
    events:
        Ordered list of events to replay. Each entry may be a dict
        (the on-the-wire / trace-store shape) or an existing
        :class:`AgentLoopEventRecord`. The order is taken as-is:
        the engine does **not** re-sort.
    goal_id:
        The goal id attached to the freshly built
        :class:`AgentLoopSession`.
    fsm:
        Optional :class:`AgentLoopFSM` override. Defaults to the
        package-level :data:`DEFAULT_FSM`.

    Returns
    -------
    :class:`ReplayResult`
        The replayed session plus the dropped-event list.
    """

    engine = fsm or DEFAULT_FSM
    session = create_session(goal_id, fsm=engine)
    # The replay session starts in ``CREATED``. The bridge may
    # have written events with ``next_state='READY'`` after the
    # ``goal_submitted`` event, so we let the FSM drive the state
    # transition naturally instead of forcing ``goal_submitted``.
    dropped: list[tuple[int, str, str]] = []
    replayed = 0
    expected = len(events)
    for item in events:
        try:
            record = (
                item
                if isinstance(item, AgentLoopEventRecord)
                else _coerce_record(item)
            )
            if session.is_terminal:
                dropped.append(
                    (
                        record.seq,
                        record.event,
                        "post_terminal",
                    )
                )
                continue
            engine.apply(session, record.event, record.payload)
            replayed += 1
        except UnknownEventError:
            # Either raised by ``_coerce_record`` (event not in
            # the typed Literal) or by the FSM itself. The seq /
            # event may be missing when ``_coerce_record`` could
            # not even extract them; use safe fallbacks.
            try:
                seq = int(getattr(item, "seq", item.get("seq", 0)))  # type: ignore[union-attr]
            except (AttributeError, TypeError, ValueError):
                seq = 0
            try:
                event_name = str(
                    getattr(item, "event", item.get("event", ""))  # type: ignore[union-attr]
                )
            except AttributeError:
                event_name = ""
            dropped.append((seq, event_name, "unknown_event"))
        except InvalidTransitionError:
            seq = int(getattr(item, "seq", 0))
            event_name = str(getattr(item, "event", ""))
            dropped.append((seq, event_name, "invalid_transition"))
        except SessionClosedError:
            seq = int(getattr(item, "seq", 0))
            event_name = str(getattr(item, "event", ""))
            dropped.append((seq, event_name, "session_closed"))
    return ReplayResult(
        session=session,
        expected_event_count=expected,
        replayed_event_count=replayed,
        dropped_events=dropped,
        final_state=session.state,
        halted=session.state in TERMINAL_STATES,
    )


def replay_session_from_trace(
    trace_store: TraceStore,
    *,
    run_id: str,
    fsm: AgentLoopFSM | None = None,
) -> ReplayResult:
    """Read the ALI event stream from ``trace_store`` and replay it.

    Reads ``ali.event`` records for ``run_id``, rebuilds an
    :class:`AgentLoopSession` from scratch, and re-applies each
    event through the supplied (or default) FSM.

    The replay is **deterministic**: given the same trace file
    contents and the same FSM, the resulting session state and
    event log are identical. The function does not call any
    side-effecting adapter, so the only inputs to the replay are
    the trace file contents and the FSM transition table.
    """

    records = _ordered_records(trace_store, run_id=run_id)
    return replay_events(
        records,
        goal_id=f"replay-{run_id}",
        fsm=fsm,
    )


def replay_trace_events(
    trace_events: list[TraceEvent],
    *,
    fsm: AgentLoopFSM | None = None,
) -> ReplayResult:
    """Replay directly from a list of :class:`TraceEvent` objects.

    Useful for tests that construct events in-memory rather than
    going through the file-backed :class:`TraceStore`. Filters on
    ``event.type == ALI_EVENT_TYPE`` and sorts by ``payload['seq']``.
    """

    filtered: list[dict[str, Any]] = []
    for event in trace_events:
        if event.type != ALI_EVENT_TYPE:
            continue
        filtered.append(dict(event.payload))
    filtered.sort(key=lambda item: int(item.get("seq", 0)))
    run_id = filtered[0].get("kernel_run_id", "replay-events") if filtered else "replay-events"
    return replay_events(
        filtered,
        goal_id=f"replay-{run_id}",
        fsm=fsm,
    )


__all__ = [
    "ReplayResult",
    "replay_events",
    "replay_session_from_trace",
    "replay_trace_events",
]