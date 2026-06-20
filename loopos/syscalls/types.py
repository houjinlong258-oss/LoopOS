"""Typed syscall contracts."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from loopos.policy_os.models import PolicyDecision

SyscallRisk = Literal["low", "medium", "high", "blocked"]
SyscallMode = Literal["guarded", "dry_run"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SyscallSpec(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    risk: SyscallRisk = "low"
    requires_approval: bool = False
    side_effecting: bool = False
    policy_scope: str
    tags: list[str] = Field(default_factory=list)

    @field_validator("name", "policy_scope")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("syscall name and policy scope are required")
        return value


class SyscallCall(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    instruction_id: str
    name: str
    input: dict[str, Any] = Field(default_factory=dict)
    workspace: str = "."
    mode: SyscallMode = "guarded"
    approval_granted: bool = False
    created_at: datetime = Field(default_factory=utc_now)


class SyscallResult(BaseModel):
    syscall_id: str
    run_id: str
    instruction_id: str
    name: str
    success: bool
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    risk: SyscallRisk = "low"
    requires_approval: bool = False
    policy_decision: PolicyDecision
    duration_ms: int = 0
    dry_run: bool = False


SyscallHandler = Callable[[SyscallCall], SyscallResult]


class RegisteredSyscall(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    spec: SyscallSpec
    handler: SyscallHandler

