"""Persistent task queue contracts for LoopOS outer-loop engineering."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


TaskStatus = Literal[
    "pending",
    "ready",
    "running",
    "waiting_review",
    "verified",
    "done",
    "blocked",
    "cancelled",
]
TaskType = Literal["code_change", "maintenance", "audit", "review", "report", "coordination"]
TaskRole = Literal["producer", "verifier", "reviewer"]
TodoStatus = Literal["pending", "done"]
TaskArtifactType = Literal["report", "patch", "pr"]
TaskArtifactStatus = Literal["draft", "ready"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TaskRecord(BaseModel):
    """Durable outer-loop task.

    Triggers create these records; they never execute work directly.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    goal: str
    description: str = ""
    type: TaskType = "coordination"
    status: TaskStatus = "pending"
    priority: int = 100
    quick_win: bool = False
    requires_worktree: bool = False
    source_trigger: str | None = None
    worktree_id: str | None = None
    review_id: str | None = None
    assigned_roles: dict[TaskRole, str] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    todos: list["TaskTodo"] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("title", "goal")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("task title and goal are required")
        return value

    def with_status(self, status: TaskStatus) -> "TaskRecord":
        clone = self.model_copy()
        clone.status = status
        clone.updated_at = utc_now()
        return clone


class TaskTodo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    text: str
    status: TodoStatus = "pending"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("text")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("todo text is required")
        return value


class TaskArtifact(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str
    type: TaskArtifactType
    title: str
    content: str
    status: TaskArtifactStatus = "draft"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("task_id", "title", "content")
    @classmethod
    def required_artifact_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("artifact fields cannot be empty")
        return value
