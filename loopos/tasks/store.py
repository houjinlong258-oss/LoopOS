"""JSON-backed persistent task queue."""

from __future__ import annotations

import json
from pathlib import Path

from loopos.tasks.models import TaskRecord, TaskStatus, utc_now


class TaskStore:
    """Small deterministic task store used by the outer loop MVP."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def list(self, *, status: TaskStatus | None = None) -> list[TaskRecord]:
        if not self.path.exists():
            return []
        payload = json.loads(self.path.read_text(encoding="utf-8") or "[]")
        tasks = [TaskRecord.model_validate(item) for item in payload]
        if status is not None:
            tasks = [task for task in tasks if task.status == status]
        return sorted(tasks, key=lambda task: (task.priority, task.created_at.isoformat()))

    def load(self, task_id: str) -> TaskRecord:
        for task in self.list():
            if task.id == task_id:
                return task
        raise KeyError(f"task not found: {task_id}")

    def create(self, task: TaskRecord) -> TaskRecord:
        self.save(task)
        return task

    def save(self, task: TaskRecord) -> TaskRecord:
        tasks = {item.id: item for item in self.list()}
        task.updated_at = utc_now()
        tasks[task.id] = task
        rows = [item.model_dump(mode="json") for item in tasks.values()]
        self.path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        return task

    def next(self, *, quick_win: bool = False) -> TaskRecord | None:
        candidates = [
            task
            for task in self.list()
            if task.status in {"pending", "ready"} and (not quick_win or task.quick_win)
        ]
        return candidates[0] if candidates else None

    def update_status(self, task_id: str, status: TaskStatus) -> TaskRecord:
        task = self.load(task_id).with_status(status)
        return self.save(task)

