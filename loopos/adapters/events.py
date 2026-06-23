"""Agent Kernel Event contract.

An :class:`AgentKernelEvent` is the only thing an adapter is allowed to
emit. The Agent Bus consumes the event stream and translates each event
into one or more governed :class:`~loopos.aci.models.AgentCommand`
objects. Events carry no authority of their own.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

AgentKernelEventKind = Literal[
    "goal_started",
    "thought",
    "plan_created",
    "tool_call_requested",
    "syscall_requested",
    "file_patch_proposed",
    "test_requested",
    "model_call_requested",
    "observation",
    "error",
    "result",
    "done",
]
"""Closed set of event kinds an adapter may emit.

The Agent Bus translation table maps the *requesting* kinds
(``file_patch_proposed``, ``syscall_requested``, ``test_requested``,
``model_call_requested``) onto ACI commands. The remaining kinds are
recorded onto the ALI session / Trace without producing a syscall.
"""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AgentKernelEvent(BaseModel):
    """Single event emitted by an adapter session.

    The event is intentionally minimal: an ``event_id`` for trace
    correlation, the originating ``session_id`` / ``adapter_id``, the
    ``kind`` discriminator, a free-form ``payload`` mapping, and an
    optional ``trace_hint``. The payload schema is interpreted by the
    Agent Bus translation layer, not here.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["0.3"] = "0.3"
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    adapter_id: str
    kind: AgentKernelEventKind
    payload: dict[str, Any] = Field(default_factory=dict)
    trace_hint: str | None = None
    created_at: datetime = Field(default_factory=_utc_now)

    @field_validator("session_id", "adapter_id")
    @classmethod
    def _required(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("value is required and must be non-empty")
        return value

    def to_json(self) -> str:
        return self.model_dump_json(exclude_none=True)

    @classmethod
    def from_json(cls, raw: str | bytes | dict[str, Any]) -> "AgentKernelEvent":
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        if isinstance(raw, str):
            data = json.loads(raw)
        else:
            data = raw
        return cls.model_validate(data)


__all__ = ["AgentKernelEvent", "AgentKernelEventKind"]
