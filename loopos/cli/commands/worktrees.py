"""Worktree isolation CLI commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from loopos.cli.commands.runtime import WorkspaceError, _check_workspace
from loopos.cli.context import data_paths
from loopos.syscalls import create_default_syscall_router
from loopos.syscalls.types import SyscallCall
from loopos.tasks import TaskStore
from loopos.worktree import WorktreeManager, WorktreeStore


def worktrees_command(
    action: str = "list",
    task_id: str | None = None,
    *,
    data_dir: str | Path = ".loopos",
    workspace: str | Path = ".",
    dry_run: bool = True,
    yes: bool = False,
) -> int:
    paths = data_paths(data_dir)
    store = WorktreeStore(paths["worktrees"])
    if action == "list":
        print(
            json.dumps(
                [item.model_dump(mode="json") for item in store.list()],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    # All non-list actions need a valid workspace.
    try:
        workspace_path = _check_workspace(workspace)
    except WorkspaceError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if action == "plan":
        if not task_id:
            print("worktrees plan requires TASK_ID.", file=sys.stderr)
            return 1
        try:
            task_store = TaskStore(paths["tasks"])
            task = task_store.load(task_id)
            record = WorktreeManager(store).plan_for_task(task)
            if record.status == "planned":
                task.worktree_id = record.id
                task.status = "ready"
                task_store.save(task)
        except (KeyError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(record.model_dump_json(indent=2))
        return 0
    if action == "stale":
        if not task_id:
            print("worktrees stale requires WORKTREE_ID.", file=sys.stderr)
            return 1
        try:
            record = WorktreeManager(store).mark_stale(task_id)
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(record.model_dump_json(indent=2))
        return 0
    if action == "cleanup":
        if not task_id:
            print("worktrees cleanup requires WORKTREE_ID.", file=sys.stderr)
            return 1
        try:
            manager = WorktreeManager(store)
            record = store.load(task_id)
            plan = manager.cleanup_plan(record, workspace=workspace_path, dry_run=dry_run)
            router = create_default_syscall_router(workspace_path, auto_approve_medium=yes)
            results = [
                router.dispatch(
                    SyscallCall(
                        run_id=f"worktree-cleanup-{record.id}",
                        instruction_id=f"worktree-cleanup-{record.id}",
                        name="terminal.exec",
                        input={"cmd": command.cmd, "timeout_seconds": 30},
                        workspace=str(workspace_path),
                        mode="dry_run" if dry_run else "guarded",
                        approval_granted=yes,
                    )
                )
                for command in plan.commands
            ]
            if not dry_run and all(result.success for result in results):
                record = manager.mark_cleaned(task_id)
        except (KeyError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(
            json.dumps(
                {
                    "record": record.model_dump(mode="json"),
                    "plan": plan.model_dump(mode="json"),
                    "results": [result.model_dump(mode="json") for result in results],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if all(result.success for result in results) else 3
    if action == "expire":
        records = WorktreeManager(store).expire_leases()
        print(json.dumps([item.model_dump(mode="json") for item in records], indent=2))
        return 0
    if action == "materialize":
        if not task_id:
            print("worktrees materialize requires WORKTREE_ID.", file=sys.stderr)
            return 1
        try:
            manager = WorktreeManager(store)
            record = store.load(task_id)
            plan = manager.materialization_plan(record, workspace=workspace_path, dry_run=dry_run)
            router = create_default_syscall_router(workspace_path, auto_approve_medium=yes)
            results = [
                router.dispatch(
                    SyscallCall(
                        run_id=f"worktree-{record.id}",
                        instruction_id=f"worktree-materialize-{record.id}",
                        name="terminal.exec",
                        input={"cmd": command.cmd, "timeout_seconds": 30},
                        workspace=str(workspace_path),
                        mode="dry_run" if dry_run else "guarded",
                        approval_granted=yes,
                    )
                )
                for command in plan.commands
            ]
            if not dry_run and all(result.success for result in results):
                record.status = "active"
                store.save(record)
        except (KeyError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(
            json.dumps(
                {
                    "plan": plan.model_dump(mode="json"),
                    "results": [result.model_dump(mode="json") for result in results],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if all(result.success for result in results) else 3
    print(f"Unknown worktrees action: {action}", file=sys.stderr)
    return 1
