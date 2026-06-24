"""Trace integration for the loop engine.

The v0.4.0 loop engine is **trace-observant**: it does not own the
trace store (that lives in ``loopos.trace``), but it produces a
sequence of ``LoopEvent`` records that the existing trace layer can
consume. This module is a thin adapter that converts loop events to
``trace.TraceEvent`` when the trace package is importable, and falls
back to a no-op recorder when it is not.
"""

from __future__ import annotations

from typing import Any, Protocol

from loopos.loop_engine.events import LoopEvent, LoopEventKind


class _TraceLike(Protocol):
    def record(self, event: Any) -> None: ...


class LoopTraceRecorder:
    """Record ``LoopEvent`` objects to a trace store when available."""

    def __init__(self, trace_store: _TraceLike | None = None) -> None:
        self._store = trace_store
        self._fallback_events: list[LoopEvent] = []

    def record(self, event: LoopEvent) -> None:
        if self._store is None:
            self._fallback_events.append(event)
            return
        try:
            self._store.record(event)
        except Exception:
            # The trace store is a support surface; never let a trace
            # failure cascade into the loop.
            self._fallback_events.append(event)

    def events(self) -> list[LoopEvent]:
        return list(self._fallback_events)

    def reset(self) -> None:
        self._fallback_events.clear()

    def kind_summary(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for e in self._fallback_events:
            key = e.kind.value if isinstance(e.kind, LoopEventKind) else str(e.kind)
            out[key] = out.get(key, 0) + 1
        return out


__all__ = ["LoopTraceRecorder"]
