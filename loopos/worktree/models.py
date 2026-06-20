"""Worktree isolation records."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


WorktreeStatus = Literal["planned", "active", "stale", "cleaned", "conflict"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WorktreeRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str
    branch: str
    path: str
    status: WorktreeStatus = "planned"
    locked_paths: list[str] = Field(default_factory=list)
    conflict_task_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("task_id", "branch", "path")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("worktree fields cannot be empty")
        return value

