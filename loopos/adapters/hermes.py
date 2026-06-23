"""Hermes Adapter proof (clean-room).

This adapter is a **clean-room** boundary for a Hermes-style external
CLI agent. No Hermes source is vendored. By default the adapter runs in
``simulated`` mode and emits a deterministic event stream; the external
CLI is only invoked when ``allow_external=True`` is explicitly passed
(and even then, every tool request becomes an
:class:`~loopos.adapters.events.AgentKernelEvent` routed through the
Agent Bus -> ACI -> Policy OS, never a direct shell bypass).
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


class HermesAdapter:
    """Clean-room Hermes CLI adapter proof (simulated by default)."""

    adapter_id: str = "hermes"
    display_name: str = "Hermes Agent"

    def __init__(self, *, allow_external: bool = False) -> None:
        self.allow_external = allow_external
        self._sessions: dict[str, AgentKernelSession] = {}
        self._event_counts: dict[str, int] = {}

    def manifest(self) -> AgentKernelManifest:
        return AgentKernelManifest(
            adapter_id=self.adapter_id,
            name=self.display_name,
            version="0.3.0",
            kind="external_cli",
            entrypoint="hermes",
            status="available",
            notes="clean-room CLI adapter proof (simulated by default)",
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
        if not self.allow_external:
            # Deterministic simulated stream — no external process.
            yield self._emit(
                session_id, "goal_started", {"goal_id": goal.goal_id, "mode": "simulated"}
            )
            yield self._emit(session_id, "plan_created", {"steps": ["inspect", "patch"]})
            yield self._emit(
                session_id,
                "syscall_requested",
                {"command": "ls", "purpose": "inspect workspace"},
            )
            yield self._emit(
                session_id,
                "file_patch_proposed",
                {"path": "src/app.py", "diff": "--- a\n+++ b\n", "purpose": "fix"},
            )
            yield self._emit(session_id, "done", {"status": "completed", "mode": "simulated"})
            return
        # External mode is intentionally not auto-wired here: it would
        # require an explicit, separately-reviewed subprocess bridge.
        yield self._emit(
            session_id,
            "error",
            {"reason_code": "external_cli_bridge_not_enabled", "adapter": self.adapter_id},
        )

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


__all__ = ["HermesAdapter"]
