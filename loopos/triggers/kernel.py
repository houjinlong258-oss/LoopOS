"""Trigger kernel that only creates tasks, never executes them."""

from __future__ import annotations

from loopos.tasks import TaskRecord, TaskStore
from loopos.triggers.models import DEFAULT_TRIGGERS, TriggerDefinition


class TriggerKernel:
    def __init__(
        self,
        task_store: TaskStore,
        triggers: dict[str, TriggerDefinition] | None = None,
    ) -> None:
        self.task_store = task_store
        self.triggers = triggers or DEFAULT_TRIGGERS

    def list(self) -> list[TriggerDefinition]:
        return list(self.triggers.values())

    def fire(self, trigger_id: str) -> TaskRecord:
        try:
            trigger = self.triggers[trigger_id]
        except KeyError as exc:
            raise KeyError(f"trigger not found: {trigger_id}") from exc
        task = TaskRecord(
            title=trigger.task_title,
            goal=trigger.task_goal,
            description=trigger.description,
            type=trigger.task_type,  # type: ignore[arg-type]
            quick_win=trigger.quick_win,
            requires_worktree=trigger.requires_worktree,
            source_trigger=trigger.id,
            tags=list(trigger.tags),
        )
        return self.task_store.create(task)

