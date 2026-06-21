"""Structured kernel signals for inter-component communication.

Signals are consumed by the scheduler, supervisor, and gateway.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class KernelSignal(str, Enum):
    """Legacy signal enum — still used by the scheduler."""
    CONTINUE = "continue"
    APPROVE = "approve"
    DENY = "deny"
    CANCEL = "cancel"
    REPAIR = "repair"
    REPLAN = "replan"
    HALT = "halt"


SignalType = Literal[
    "pause",
    "resume",
    "cancel",
    "approve",
    "deny",
    "interrupt",
    "request_status",
    "request_trace",
    "force_checkpoint",
]

SignalSource = Literal["cli", "gateway", "policy", "system", "test"]


class KernelSignalEvent(BaseModel):
    """Typed signal event for the kernel dispatch system."""

    signal_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    signal_type: SignalType
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utc_now)
    source: SignalSource = "system"
