"""LoopOS Trace Runtime.

This package wraps the existing kernel trace runtime
(:mod:`loopos.kernel.trace`) with thin bridges that translate
cross-layer events into the trace shape the runtime already
accepts.

Public surface:

* :mod:`loopos.trace.ali_bridge` -- persist and replay ALI event
  records through the existing :class:`TraceStore`.
"""

from loopos.trace.ali_bridge import (
    ALI_EVENT_TYPE,
    persist_session_events,
    replay_session_events,
)

__all__ = [
    "ALI_EVENT_TYPE",
    "persist_session_events",
    "replay_session_events",
]