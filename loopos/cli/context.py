"""Shared CLI paths and runtime context helpers."""

from __future__ import annotations

from pathlib import Path


def data_paths(data_dir: str | Path) -> dict[str, Path]:
    base = Path(data_dir)
    return {
        "base": base,
        "events": base / "events.jsonl",
        "runs": base / "runs",
        "skills": base / "skills.jsonl",
        "beliefs": base / "beliefs.jsonl",
        "policy_audit": base / "policy_audit.jsonl",
        "tasks": base / "tasks.json",
        "task_artifacts": base / "task_artifacts.json",
        "worktrees": base / "worktrees.json",
        "reviews": base / "reviews.json",
        "gateway_messages": base / "gateway_messages.json",
        "gateway_approvals": base / "gateway_approvals.json",
    }
