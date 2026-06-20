"""Trigger definitions for LoopOS outer-loop tasks."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


TriggerAction = Literal["create_task"]


class TriggerDefinition(BaseModel):
    id: str
    description: str = ""
    action: TriggerAction = "create_task"
    task_title: str
    task_goal: str
    task_type: str = "maintenance"
    quick_win: bool = False
    requires_worktree: bool = False
    tags: list[str] = Field(default_factory=list)

    @field_validator("id", "task_title", "task_goal")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("trigger fields cannot be empty")
        return value


DEFAULT_TRIGGERS: dict[str, TriggerDefinition] = {
    "daily-maintenance": TriggerDefinition(
        id="daily-maintenance",
        description="Create a low-risk repository maintenance task.",
        task_title="Daily maintenance audit",
        task_goal="Review repository health, test status, and small quick-win improvements.",
        task_type="maintenance",
        quick_win=True,
        requires_worktree=False,
        tags=["maintenance", "quick-win"],
    ),
    "code-improvement": TriggerDefinition(
        id="code-improvement",
        description="Create a code-change task that requires isolated worktree handling.",
        task_title="Isolated code improvement",
        task_goal="Implement one scoped code improvement in an isolated worktree.",
        task_type="code_change",
        quick_win=False,
        requires_worktree=True,
        tags=["code", "worktree"],
    ),
}

