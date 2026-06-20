"""JSON-backed persistent task queue."""

from __future__ import annotations

import json
from pathlib import Path

from loopos.tasks.models import TaskArtifact, TaskArtifactType, TaskRecord, TaskStatus, TaskTodo, utc_now


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

    def add_todo(self, task_id: str, text: str) -> TaskRecord:
        task = self.load(task_id)
        task.todos.append(TaskTodo(text=text))
        return self.save(task)

    def complete_todo(self, task_id: str, todo_id: str) -> TaskRecord:
        task = self.load(task_id)
        for todo in task.todos:
            if todo.id == todo_id:
                todo.status = "done"
                todo.updated_at = utc_now()
                return self.save(task)
        raise KeyError(f"todo not found: {todo_id}")


class TaskArtifactStore:
    """JSON-backed report, patch, and PR artifact store."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def list(
        self,
        *,
        task_id: str | None = None,
        artifact_type: TaskArtifactType | None = None,
    ) -> list[TaskArtifact]:
        if not self.path.exists():
            return []
        rows = json.loads(self.path.read_text(encoding="utf-8") or "[]")
        artifacts = [TaskArtifact.model_validate(item) for item in rows]
        if task_id is not None:
            artifacts = [item for item in artifacts if item.task_id == task_id]
        if artifact_type is not None:
            artifacts = [item for item in artifacts if item.type == artifact_type]
        return sorted(artifacts, key=lambda item: item.created_at.isoformat())

    def save(self, artifact: TaskArtifact) -> TaskArtifact:
        artifacts = {item.id: item for item in self.list()}
        artifact.updated_at = utc_now()
        artifacts[artifact.id] = artifact
        self.path.write_text(
            json.dumps(
                [item.model_dump(mode="json") for item in artifacts.values()],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return artifact

    def create(
        self,
        *,
        task_id: str,
        artifact_type: TaskArtifactType,
        title: str,
        content: str,
        ready: bool = False,
    ) -> TaskArtifact:
        return self.save(
            TaskArtifact(
                task_id=task_id,
                type=artifact_type,
                title=title,
                content=content,
                status="ready" if ready else "draft",
            )
        )
