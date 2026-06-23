"""Deterministic Mock Adapter.

The :class:`MockAdapter` is the reference adapter used by the test
suite and the Workbench dry-run path. It emits a fixed, deterministic
event stream that exercises every translatable event kind without any
external process, network, or filesystem effect.
"""

from __future__ import annotations

from typing import Any, Iterable

from loopos.adapters.base import (
    AgentKernelCapabilities,
    AgentKernelSession,
    AgentKernelSnapshot,
    GoalSpec,
)
from loopos.adapters.events import AgentKernelEvent
from loopos.adapters.manifest import (
    AgentKernelAuthority,
    AgentKernelCapabilitiesModel,
    AgentKernelManifest,
)


class MockAdapter:
    """A deterministic native adapter for tests and dry-runs."""

    adapter_id: str = "mock"
    display_name: str = "Mock Adapter"

    def __init__(self) -> None:
        self._sessions: dict[str, AgentKernelSession] = {}
        self._event_counts: dict[str, int] = {}

    def manifest(self) -> AgentKernelManifest:
        return AgentKernelManifest(
            adapter_id=self.adapter_id,
            name=self.display_name,
            version="0.3.0",
            kind="native",
            entrypoint="builtin",
            status="ready",
            notes="deterministic test adapter",
            capabilities=AgentKernelCapabilitiesModel(
                streaming_events=True,
                file_patch=True,
                shell_request=True,
                model_call_request=True,
                snapshot_resume=True,
            ),
            authority=AgentKernelAuthority(
                direct_shell=False,
                direct_file_write=False,
                requires_aci=True,
                requires_policy=True,
                requires_trace=True,
            ),
        )

    def capabilities(self) -> AgentKernelCapabilities:
        return AgentKernelCapabilities(
            streaming_events=True,
            file_patch=True,
            shell_request=True,
            model_call_request=True,
            snapshot_resume=True,
        )

    def start_session(self, goal: GoalSpec) -> AgentKernelSession:
        session = AgentKernelSession(adapter_id=self.adapter_id, goal=goal)
        self._sessions[session.session_id] = session
        self._event_counts[session.session_id] = 0
        return session

    def _emit(self, session_id: str, kind: Any, payload: dict[str, Any]) -> AgentKernelEvent:
        self._event_counts[session_id] = self._event_counts.get(session_id, 0) + 1
        return AgentKernelEvent(
            session_id=session_id,
            adapter_id=self.adapter_id,
            kind=kind,
            payload=payload,
        )

    def submit_goal(self, session_id: str, goal: GoalSpec) -> Iterable[AgentKernelEvent]:
        """Emit a fixed deterministic event stream for the goal."""
        yield self._emit(session_id, "goal_started", {"goal_id": goal.goal_id, "title": goal.title})
        yield self._emit(session_id, "thought", {"text": "analyze goal"})
        yield self._emit(session_id, "plan_created", {"steps": ["read", "test", "patch"]})
        yield self._emit(
            session_id,
            "test_requested",
            {"command": "python -m pytest -q", "purpose": "verify baseline"},
        )
        yield self._emit(
            session_id,
            "file_patch_proposed",
            {"path": "README.md", "diff": "--- a\n+++ b\n", "purpose": "doc update"},
        )
        yield self._emit(
            session_id,
            "model_call_requested",
            {"provider_id": "mock", "model_id": "mock-model", "prompt": "summarize"},
        )
        yield self._emit(session_id, "observation", {"text": "tests green"})
        yield self._emit(session_id, "result", {"summary": "goal addressed"})
        yield self._emit(session_id, "done", {"status": "completed"})

    def submit_command(self, session_id: str, command: Any) -> Iterable[AgentKernelEvent]:
        yield self._emit(session_id, "observation", {"echo": str(command)})
        yield self._emit(session_id, "done", {"status": "completed"})

    def snapshot(self, session_id: str) -> AgentKernelSnapshot:
        session = self._sessions[session_id]
        return AgentKernelSnapshot(
            session_id=session_id,
            adapter_id=self.adapter_id,
            goal=session.goal,
            state=session.state,
            event_count=self._event_counts.get(session_id, 0),
        )

    def resume(self, snapshot: AgentKernelSnapshot) -> AgentKernelSession:
        session = AgentKernelSession(
            session_id=snapshot.session_id,
            adapter_id=self.adapter_id,
            goal=snapshot.goal,
            state=snapshot.state,
        )
        self._sessions[session.session_id] = session
        self._event_counts[session.session_id] = snapshot.event_count
        return session

    def cancel(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._event_counts.pop(session_id, None)


__all__ = ["MockAdapter"]
