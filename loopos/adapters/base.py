"""Agent Kernel Adapter base protocol and session models.

The :class:`AgentKernelAdapter` Protocol defines the universal contract
every adapter must satisfy. The :class:`AgentKernelSession` and
:class:`AgentKernelSnapshot` are concrete Pydantic models so sessions
can be serialized, replayed, and inspected.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Protocol, runtime_checkable
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from loopos.adapters.events import AgentKernelEvent
from loopos.adapters.manifest import AgentKernelManifest


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AgentKernelCapabilities(BaseModel):
    """Runtime-resolved capability snapshot for an adapter."""

    model_config = ConfigDict(extra="forbid")

    streaming_events: bool = True
    file_patch: bool = False
    shell_request: bool = False
    model_call_request: bool = False
    snapshot_resume: bool = False


class GoalSpec(BaseModel):
    """Minimal goal contract handed to an adapter session."""

    model_config = ConfigDict(extra="forbid")

    goal_id: str = Field(default_factory=lambda: f"goal_{uuid4().hex[:8]}")
    title: str = ""
    intent: str = ""
    acceptance: str = ""
    risk: str = "medium"


class AgentKernelSession(BaseModel):
    """Live adapter session handle."""

    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(default_factory=lambda: f"aks_{uuid4().hex[:8]}")
    adapter_id: str
    goal: GoalSpec = Field(default_factory=GoalSpec)
    state: str = "started"
    created_at: datetime = Field(default_factory=_utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentKernelSnapshot(BaseModel):
    """Serializable snapshot of an adapter session for resume."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    adapter_id: str
    goal: GoalSpec = Field(default_factory=GoalSpec)
    state: str = "started"
    event_count: int = 0
    created_at: datetime = Field(default_factory=_utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class AgentKernelAdapter(Protocol):
    """Universal adapter contract for any external or native agent kernel."""

    adapter_id: str
    display_name: str

    def manifest(self) -> AgentKernelManifest: ...

    def capabilities(self) -> AgentKernelCapabilities: ...

    def start_session(self, goal: GoalSpec) -> AgentKernelSession: ...

    def submit_goal(self, session_id: str, goal: GoalSpec) -> Iterable[AgentKernelEvent]: ...

    def submit_command(self, session_id: str, command: Any) -> Iterable[AgentKernelEvent]: ...

    def snapshot(self, session_id: str) -> AgentKernelSnapshot: ...

    def resume(self, snapshot: AgentKernelSnapshot) -> AgentKernelSession: ...

    def cancel(self, session_id: str) -> None: ...


__all__ = [
    "AgentKernelAdapter",
    "AgentKernelCapabilities",
    "AgentKernelSession",
    "AgentKernelSnapshot",
    "GoalSpec",
]
