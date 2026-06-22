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

Maintainability note (Phase 3.x):

The Phase 3 ACI result consumption logic (``consume_aci_result``
and its private helpers) has been split out into
:mod:`loopos.ali.aci_consumption` so this module stays focused on
session lifecycle (creation + event application). The consumer is
re-exported here so the public ALI surface (``from loopos.ali
import consume_aci_result``) is unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loopos.ali.aci_consumption import consume_aci_result
from loopos.ali.errors import (
    InvalidTransitionError,
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


def to_event_stream(session: AgentLoopSession) -> list[dict[str, Any]]:
    """Return the session's events as a deterministic ordered stream.

    Each entry contains:

    * ``seq`` -- 0-indexed position in the session's event log.
    * ``event`` -- the :class:`AgentLoopEvent` that fired.
    * ``reason_code`` -- the FSM transition row's reason code.
    * ``next_state`` -- the state the FSM transitioned into.
    * ``payload`` -- a copy of the structured payload attached to
      the event record.
    * ``created_at`` -- ISO-8601 timestamp.

    The output is deterministic: same session state -> same stream.
    The trace bridge consumes this list (or the underlying
    :attr:`AgentLoopSession.events` list) and persists one trace
    event per record.

    Phase 5: introduced so the trace bridge can replay the full ALI
    event sequence without re-running the FSM.
    """

    return [
        {
            "seq": record.seq,
            "event": record.event,
            "reason_code": record.reason_code,
            "next_state": record.next_state,
            "payload": dict(record.payload),
            "created_at": record.created_at.isoformat(),
        }
        for record in session.events
    ]


__all__ = [
    "SessionConfig",
    "apply_event",
    "consume_aci_result",
    "create_session",
    "to_event_stream",
]