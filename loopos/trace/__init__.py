"""LoopOS Trace Runtime.

This package wraps the existing kernel trace runtime
(:mod:`loopos.kernel.trace`) with thin bridges that translate
cross-layer events into the trace shape the runtime already
accepts.

Public surface:

* :mod:`loopos.trace.ali_bridge` -- persist and replay ALI event
  records through the existing :class:`TraceStore`.
* :mod:`loopos.trace.ali_replay` -- ALI Replay Engine: rebuild a
  fresh :class:`AgentLoopSession` from the persisted ``ali.event``
  record stream without re-running ACI / Policy OS / Syscall
  Router. Provides the deterministic replay proof surface for
  the v0.2 readiness check.
"""

from loopos.trace.ali_bridge import (
    ALI_EVENT_TYPE,
    persist_session_events,
    replay_session_events,
)
from loopos.trace.ali_replay import (
    ReplayResult,
    replay_events,
    replay_session_from_trace,
    replay_trace_events,
)

__all__ = [
    "ALI_EVENT_TYPE",
    "ReplayResult",
    "persist_session_events",
    "replay_events",
    "replay_session_events",
    "replay_session_from_trace",
    "replay_trace_events",
]