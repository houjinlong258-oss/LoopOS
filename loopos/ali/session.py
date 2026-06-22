"""Session helpers for the Agent Loop Interface.

A session is a thin owner of an :class:`AgentLoopFSM` plus a typed
:func:`apply_event` convenience. The session can serialize itself
through Pydantic, can reference an :class:`AgentCommandResult` without
importing the ACI package, and has no side effects beyond mutating its
own state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loopos.ali.errors import InvalidTransitionError, UnknownEventError
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
