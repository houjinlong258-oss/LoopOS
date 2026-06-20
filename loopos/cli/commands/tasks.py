"""Persistent task CLI commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from loopos.cli.context import data_paths
from loopos.tasks import TaskArtifactStore, TaskRecord, TaskStore


def tasks_command(
    action: str = "list",
    arg: str | None = None,
    *,
    data_dir: str | Path = ".loopos",
    quick_win: bool = False,
    json_output: bool = False,
    goal: str | None = None,
    task_type: str = "coordination",
    text: str | None = None,
    content: str | None = None,
    title: str | None = None,
    requires_worktree: bool = False,
    ready: bool = False,
) -> int:
    paths = data_paths(data_dir)
    store = TaskStore(paths["tasks"])
    artifacts = TaskArtifactStore(paths["task_artifacts"])
    if action == "list":
        tasks = store.list()
        if json_output:
            print(
                json.dumps(
                    [task.model_dump(mode="json") for task in tasks],
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif not tasks:
            print("No tasks stored.")
        else:
            for task in tasks:
                marker = " quick-win" if task.quick_win else ""
                print(f"{task.id} [{task.status}] {task.title}{marker}")
        return 0
    if action == "next":
        next_task = store.next(quick_win=quick_win)
        if next_task is None:
            print("No matching task.")
            return 0
        print(next_task.model_dump_json(indent=2))
        return 0
    if action == "create":
        if not arg:
            print("tasks create requires TITLE.", file=sys.stderr)
            return 1
        try:
            task = store.create(
                TaskRecord(
                    title=arg,
                    goal=goal or arg,
                    type=task_type,  # type: ignore[arg-type]
                    quick_win=quick_win,
                    requires_worktree=requires_worktree or task_type == "code_change",
                )
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(task.model_dump_json(indent=2))
        return 0
    if action == "show":
        if not arg:
            print("tasks show requires TASK_ID.", file=sys.stderr)
            return 1
        try:
            task = store.load(arg)
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(task.model_dump_json(indent=2))
        return 0
    if action == "todo":
        if not arg or not text:
            print("tasks todo requires TASK_ID and --text TEXT.", file=sys.stderr)
            return 1
        try:
            task = store.add_todo(arg, text)
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(task.model_dump_json(indent=2))
        return 0
    if action == "done":
        if not arg or not text:
            print("tasks done requires TASK_ID and --text TODO_ID.", file=sys.stderr)
            return 1
        try:
            task = store.complete_todo(arg, text)
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(task.model_dump_json(indent=2))
        return 0
    if action in {"report", "patch", "pr"}:
        if not arg or not content:
            print(f"tasks {action} requires TASK_ID and --content TEXT.", file=sys.stderr)
            return 1
        try:
            store.load(arg)
            artifact = artifacts.create(
                task_id=arg,
                artifact_type=action,  # type: ignore[arg-type]
                title=title or f"{action} for {arg}",
                content=content,
                ready=ready,
            )
        except (KeyError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(artifact.model_dump_json(indent=2))
        return 0
    if action == "artifacts":
        rows = artifacts.list(task_id=arg)
        print(
            json.dumps(
                [item.model_dump(mode="json") for item in rows],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    print(f"Unknown tasks action: {action}", file=sys.stderr)
    return 1
