"""Agent Bus — observability events.

The :class:`AgentBusEvent` is a serializable record of something that
happened inside the bus. It is not the same as an
:class:`~loopos.adapters.events.AgentKernelEvent`; the bus event is
the bus's own view of what it did with an incoming adapter event.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


AgentBusEventKind = Literal[
    "event_received",
    "event_translated",
    "command_dispatched",
    "command_blocked",
    "session_attached",
    "session_detached",
    "policy_denied",
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AgentBusEvent(BaseModel):
    """A single bus-side event for trace / observability."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "0.3"
    event_id: str = Field(default_factory=lambda: f"bus_{uuid4().hex[:10]}")
    kind: AgentBusEventKind
    session_id: str
    adapter_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utc_now)


__all__ = ["AgentBusEvent", "AgentBusEventKind"]
