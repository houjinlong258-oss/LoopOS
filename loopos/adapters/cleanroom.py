"""Clean-room Codex / Claude Code adapter spec.

This module defines the boundary for a clean-room Codex / Claude Code
style adapter. It only defines the contract and a mock event stream;
it does not depend on, import, or reproduce any private implementation.
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


class CleanroomAdapter:
    """Clean-room spec adapter for Codex / Claude Code style kernels."""

    adapter_id: str = "cleanroom"
    display_name: str = "Clean-room Codex/Claude Code"

    def __init__(self) -> None:
        self._sessions: dict[str, AgentKernelSession] = {}
        self._event_counts: dict[str, int] = {}

    def manifest(self) -> AgentKernelManifest:
        return AgentKernelManifest(
            adapter_id=self.adapter_id,
            name=self.display_name,
            version="0.3.0",
            kind="spec_only",
            entrypoint="",
            status="spec_only",
            notes="clean-room boundary spec; no private implementation dependency",
            capabilities=AgentKernelCapabilitiesModel(
                streaming_events=True,
                file_patch=True,
                shell_request=True,
                model_call_request=True,
                snapshot_resume=False,
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
            snapshot_resume=False,
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
        yield self._emit(session_id, "goal_started", {"goal_id": goal.goal_id, "mode": "mock"})
        yield self._emit(session_id, "done", {"status": "completed", "mode": "mock"})

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
        return session

    def cancel(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._event_counts.pop(session_id, None)


__all__ = ["CleanroomAdapter"]
