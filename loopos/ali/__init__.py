"""Agent Loop Interface (ALI).

ALI is the Agent Loop Interface: it defines the governed finite-state
machine that an ACI result drives inside a LoopOS run. ALI does not
import ``loopos.kernel.*`` and does not touch ``KernelLoopEngine``;
the v0.1 Kernel loop engine is the existing v0.1 implementation. ALI
exposes the typed contracts that a Phase 1+ loop engine can speak
without rewriting the runtime.

This package is intentionally small:

* :mod:`loopos.ali.models` - typed states, events, and session.
* :mod:`loopos.ali.fsm` - :class:`AgentLoopFSM` driven by a transition
  table.
* :mod:`loopos.ali.session` - :class:`AgentLoopSession` that owns the
  FSM, accumulates events, references ACI results, and (Phase 3)
  drives the FSM from a real :class:`AgentCommandResult`.
* :mod:`loopos.ali.errors` - typed errors raised by the ALI layer.
"""

from loopos.ali.errors import (
    AliError,
    InvalidTransitionError,
    SessionClosedError,
    UnknownEventError,
)
from loopos.ali.fsm import AgentLoopFSM, TransitionRow
from loopos.ali.models import (
    AgentLoopEvent,
    AgentLoopSession,
    AgentLoopState,
    ConvergenceSignal,
)
from loopos.ali.session import (
    SessionConfig,
    apply_event,
    consume_aci_result,
    create_session,
)

__all__ = [
    "AgentLoopEvent",
    "AgentLoopFSM",
    "AgentLoopSession",
    "AgentLoopState",
    "AliError",
    "ConvergenceSignal",
    "InvalidTransitionError",
    "SessionClosedError",
    "SessionConfig",
    "TransitionRow",
    "UnknownEventError",
    "apply_event",
    "consume_aci_result",
    "create_session",
]
