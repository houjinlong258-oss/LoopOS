"""Worktree isolation records."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


WorktreeStatus = Literal["planned", "active", "stale", "cleaned", "conflict"]
WorktreeCommandRisk = Literal["medium", "high"]
WorktreeLeaseStatus = Literal["active", "expired", "released"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WorktreeRecord(BaseModel):
    schema_version: str = "1.1"
    id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str
    branch: str
    path: str
    status: WorktreeStatus = "planned"
    locked_paths: list[str] = Field(default_factory=list)
    conflict_task_ids: list[str] = Field(default_factory=list)
    owner_id: str = "outer-loop"
    run_id: str | None = None
    lease_id: str | None = None
    lease_expires_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("task_id", "branch", "path")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("worktree fields cannot be empty")
        return value


class WorktreeCommand(BaseModel):
    purpose: str
    cmd: str
    risk: WorktreeCommandRisk = "medium"
    requires_approval: bool = True

    @field_validator("purpose", "cmd")
    @classmethod
    def required_command_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("worktree command fields cannot be empty")
        return value


class WorktreeExecutionPlan(BaseModel):
    worktree_id: str
    task_id: str
    workspace: str
    dry_run: bool = True
    commands: list[WorktreeCommand] = Field(default_factory=list)


class WorktreeLease(BaseModel):
    schema_version: str = "1.0"
    id: str = Field(default_factory=lambda: str(uuid4()))
    worktree_id: str
    task_id: str
    owner_id: str
    run_id: str | None = None
    status: WorktreeLeaseStatus = "active"
    acquired_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime
    released_at: datetime | None = None
