"""ChatOps gateway event contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


GatewayChannel = Literal[
    "webhook",
    "telegram",
    "email",
    "slack",
    "discord",
    "whatsapp_cloud",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AttachmentMetadata(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    filename: str
    media_type: str = "application/octet-stream"
    size_bytes: int = Field(default=0, ge=0)
    sha256: str | None = None
    local_reference: str | None = None


class GatewayAuthResult(BaseModel):
    channel: GatewayChannel
    user_id: str
    allowed: bool
    reason_code: str


class MessageEvent(BaseModel):
    schema_version: str = "1.1"
    id: str = Field(default_factory=lambda: str(uuid4()))
    channel: GatewayChannel
    user_id: str
    text: str
    thread_id: str | None = None
    run_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    attachments: list[AttachmentMetadata] = Field(default_factory=list)
    authenticated: bool = False
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("user_id", "text")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message user and text are required")
        return value


class ApprovalCard(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    channel: GatewayChannel
    run_id: str
    action_summary: str
    risk: Literal["medium", "high", "blocked"]
    reason_codes: list[str] = Field(default_factory=list)
    status: Literal["pending", "approved", "denied"] = "pending"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    decided_at: datetime | None = None


class ApprovalResumeDecision(BaseModel):
    card_id: str
    run_id: str
    approve: bool = False
    deny: bool = False
    status: Literal["approved", "denied"]
    signal: Literal["approve", "deny"]


class DeliveryRecord(BaseModel):
    schema_version: str = "1.0"
    id: str = Field(default_factory=lambda: str(uuid4()))
    channel: GatewayChannel
    user_id: str
    message_id: str | None = None
    status: Literal["queued", "delivered", "failed"] = "queued"
    payload_summary: str = ""
    created_at: datetime = Field(default_factory=utc_now)


class GatewaySession(BaseModel):
    schema_version: str = "1.0"
    id: str = Field(default_factory=lambda: str(uuid4()))
    channel: GatewayChannel
    user_id: str
    thread_id: str | None = None
    run_id: str | None = None
    active: bool = True
    updated_at: datetime = Field(default_factory=utc_now)
