"""Provider Runtime data models.

These models define the **vendor-neutral** request/response contract.
No vendor-private logic lives here: an OpenAI call, an Anthropic call,
and an Ollama call all flow through the same
:class:`ModelCallRequest` / :class:`ModelCallResponse`.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

ModelRole = Literal["system", "user", "assistant", "tool"]

ModelCallStatus = Literal["completed", "blocked", "failed", "rate_limited", "dry_run"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ModelMessage(BaseModel):
    """Single chat message."""

    model_config = ConfigDict(extra="forbid")

    role: ModelRole
    content: str = ""

    @field_validator("role")
    @classmethod
    def _role_required(cls, value: str) -> str:
        if not value:
            raise ValueError("role is required")
        return value


class ModelUsage(BaseModel):
    """Token / cost accounting for a single model call."""

    model_config = ConfigDict(extra="forbid")

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class ModelCallRequest(BaseModel):
    """Vendor-neutral model call request.

    ``live_provider_calls_allowed`` defaults to ``False``: a runtime
    must refuse to make a network call unless this is explicitly set
    True *and* a budget is supplied.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["0.3"] = "0.3"
    request_id: str = Field(default_factory=lambda: f"req_{uuid4().hex[:10]}")
    provider_id: str
    model_id: str
    messages: list[ModelMessage] = Field(default_factory=list)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)
    json_schema: dict[str, Any] | None = None
    stream: bool = False
    budget_usd: float | None = Field(default=None, ge=0.0)
    trace_required: bool = True
    live_provider_calls_allowed: bool = False
    base_url: str = ""
    created_at: datetime = Field(default_factory=_utc_now)

    @field_validator("provider_id", "model_id")
    @classmethod
    def _required(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("value is required and must be non-empty")
        return value

    def to_json(self) -> str:
        return self.model_dump_json(exclude_none=True)


class ModelCallResponse(BaseModel):
    """Vendor-neutral model call response."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["0.3"] = "0.3"
    request_id: str
    provider_id: str
    model_id: str
    status: ModelCallStatus
    content: str | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    usage: ModelUsage | None = None
    reason_codes: list[str] = Field(default_factory=list)
    trace_id: str | None = None
    created_at: datetime = Field(default_factory=_utc_now)

    def to_json(self) -> str:
        return self.model_dump_json(exclude_none=True)

    @classmethod
    def from_json(cls, raw: str | bytes | dict[str, Any]) -> "ModelCallResponse":
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        if isinstance(raw, str):
            data = json.loads(raw)
        else:
            data = raw
        return cls.model_validate(data)


__all__ = [
    "ModelRole",
    "ModelCallStatus",
    "ModelMessage",
    "ModelUsage",
    "ModelCallRequest",
    "ModelCallResponse",
]
