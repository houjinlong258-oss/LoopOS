"""Agent Bus — session bookkeeping.

The :class:`AgentBusSession` is a small Pydantic model that records
the binding between an adapter session and an ALI session. It is
purely informational: the bus uses it to look up the ALI session id
when dispatching a command, but it does not own the lifecycle of
either session.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AgentBusSession(BaseModel):
    """Binding between an adapter session and an ALI session."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "0.3"
    bus_session_id: str = Field(default_factory=lambda: f"abs_{uuid4().hex[:10]}")
    adapter_session_id: str
    adapter_id: str
    ali_session_id: str
    attached_at: datetime = Field(default_factory=_utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


__all__ = ["AgentBusSession"]
