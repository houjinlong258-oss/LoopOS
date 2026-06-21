"""Safe worktree registry for outer-loop code tasks."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import timedelta
from pathlib import Path

from loopos.tasks import TaskRecord
from loopos.worktree.models import (
    WorktreeCommand,
    WorktreeExecutionPlan,
    WorktreeLease,
    WorktreeRecord,
    WorktreeStatus,
    utc_now,
)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-").lower()
    return slug[:40] or "task"


class WorktreeStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def list(self, *, status: WorktreeStatus | None = None) -> list[WorktreeRecord]:
        if not self.path.exists():
            return []
        rows = json.loads(self.path.read_text(encoding="utf-8") or "[]")
        records = [WorktreeRecord.model_validate(item) for item in rows]
        if status is not None:
            records = [record for record in records if record.status == status]
        return sorted(records, key=lambda item: item.created_at.isoformat())

    def load(self, worktree_id: str) -> WorktreeRecord:
        for record in self.list():
            if record.id == worktree_id:
                return record
        raise KeyError(f"worktree not found: {worktree_id}")

    def save(self, record: WorktreeRecord) -> WorktreeRecord:
        records = {item.id: item for item in self.list()}
        record.updated_at = utc_now()
        records[record.id] = record
        self.path.write_text(
            json.dumps(
                [item.model_dump(mode="json") for item in records.values()],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return record


class WorktreeManager:
    """Registers isolated worktree plans without bypassing Policy OS for git commands."""

    def __init__(self, store: WorktreeStore, *, base_dir: str | Path = ".loopos-worktrees") -> None:
        self.store = store
        self.base_dir = Path(base_dir)

    def plan_for_task(
        self,
        task: TaskRecord,
        *,
        locked_paths: list[str] | None = None,
        owner_id: str = "outer-loop",
        run_id: str | None = None,
        lease_seconds: int = 3600,
    ) -> WorktreeRecord:
        if not task.requires_worktree:
            raise ValueError("task does not require a worktree")
        branch = f"codex/{_slug(task.title)}-{task.id[:8]}"
        path = self.base_dir / _slug(f"{task.id}-{task.title}")
        expires_at = utc_now() + timedelta(seconds=max(60, lease_seconds))
        record = WorktreeRecord(
            task_id=task.id,
            branch=branch,
            path=str(path),
            locked_paths=locked_paths or ["."],
            owner_id=owner_id,
            run_id=run_id,
            lease_expires_at=expires_at,
        )
        lease = WorktreeLease(
            worktree_id=record.id,
            task_id=task.id,
            owner_id=owner_id,
            run_id=run_id,
            expires_at=expires_at,
        )
        record.lease_id = lease.id
        conflicts = self.detect_conflicts(record)
        if conflicts:
            record.status = "conflict"
            record.conflict_task_ids = [item.task_id for item in conflicts]
        return self.store.save(record)

    def detect_conflicts(self, candidate: WorktreeRecord) -> list[WorktreeRecord]:
        candidate_locks = set(candidate.locked_paths or ["."])
        conflicts: list[WorktreeRecord] = []
        for record in self.store.list():
            if record.id == candidate.id or record.status in {"cleaned", "stale"}:
                continue
            if self.is_expired(record):
                continue
            if Path(record.path) == Path(candidate.path):
                conflicts.append(record)
                continue
            if candidate_locks.intersection(record.locked_paths or ["."]):
                conflicts.append(record)
        return conflicts

    def mark_stale(self, worktree_id: str) -> WorktreeRecord:
        record = self.store.load(worktree_id)
        record.status = "stale"
        return self.store.save(record)

    def mark_cleaned(self, worktree_id: str) -> WorktreeRecord:
        record = self.store.load(worktree_id)
        if record.status not in {"stale", "active"}:
            raise ValueError("only active or stale worktrees can be marked cleaned")
        record.status = "cleaned"
        return self.store.save(record)

    def expire_leases(self) -> list[WorktreeRecord]:
        expired: list[WorktreeRecord] = []
        for record in self.store.list():
            if record.status in {"planned", "active"} and self.is_expired(record):
                record.status = "stale"
                expired.append(self.store.save(record))
        return expired

    @staticmethod
    def is_expired(record: WorktreeRecord) -> bool:
        return bool(record.lease_expires_at and record.lease_expires_at <= utc_now())

    def cleanup_plan(
        self,
        record: WorktreeRecord,
        *,
        workspace: str | Path,
        dry_run: bool = True,
    ) -> WorktreeExecutionPlan:
        if record.status not in {"stale", "active"}:
            raise ValueError("only active or stale worktrees can be cleaned")
        command = subprocess.list2cmdline(["git", "worktree", "remove", record.path])
        return WorktreeExecutionPlan(
            worktree_id=record.id,
            task_id=record.task_id,
            workspace=str(Path(workspace).resolve()),
            dry_run=dry_run,
            commands=[
                WorktreeCommand(
                    purpose="remove isolated git worktree",
                    cmd=command,
                    risk="high",
                    requires_approval=True,
                )
            ],
        )

    def materialization_plan(
        self,
        record: WorktreeRecord,
        *,
        workspace: str | Path,
        dry_run: bool = True,
    ) -> WorktreeExecutionPlan:
        if record.status == "conflict":
            raise ValueError("conflicting worktrees cannot be materialized")
        if record.status in {"cleaned", "stale"}:
            raise ValueError("inactive worktrees cannot be materialized")
        command = subprocess.list2cmdline(
            ["git", "worktree", "add", "-b", record.branch, record.path]
        )
        return WorktreeExecutionPlan(
            worktree_id=record.id,
            task_id=record.task_id,
            workspace=str(Path(workspace).resolve()),
            dry_run=dry_run,
            commands=[
                WorktreeCommand(
                    purpose="create isolated git worktree",
                    cmd=command,
                    risk="medium",
                    requires_approval=True,
                )
            ],
        )
