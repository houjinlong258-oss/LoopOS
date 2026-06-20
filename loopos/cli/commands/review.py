"""Producer, verifier, and reviewer CLI commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from loopos.cli.context import data_paths
from loopos.review import ReviewCoordinator, ReviewStore
from loopos.tasks import TaskStore


def review_command(
    action: str = "list",
    task_id: str | None = None,
    *,
    data_dir: str | Path = ".loopos",
    producer: str = "producer",
    verifier: str = "verifier",
    reviewer: str = "reviewer",
    actor: str | None = None,
    note: str | None = None,
) -> int:
    paths = data_paths(data_dir)
    store = ReviewStore(paths["reviews"])
    coordinator = ReviewCoordinator(store)
    if action == "list":
        print(
            json.dumps(
                [item.model_dump(mode="json") for item in store.list()],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if action == "start":
        if not task_id:
            print("review start requires TASK_ID.", file=sys.stderr)
            return 1
        try:
            task = TaskStore(paths["tasks"]).load(task_id)
            review = coordinator.start(
                task,
                producer=producer,
                verifier=verifier,
                reviewer=reviewer,
            )
        except (KeyError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        task.review_id = review.id
        TaskStore(paths["tasks"]).save(task)
        print(review.model_dump_json(indent=2))
        return 0
    if action == "verify":
        if not task_id or not note:
            print("review verify requires REVIEW_ID and --note TEXT.", file=sys.stderr)
            return 1
        try:
            review = coordinator.verify(task_id, actor=actor or verifier, note=note)
        except (KeyError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(review.model_dump_json(indent=2))
        return 0
    if action == "approve":
        if not task_id:
            print("review approve requires REVIEW_ID.", file=sys.stderr)
            return 1
        try:
            review = coordinator.approve(task_id, actor=actor or reviewer)
        except (KeyError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(review.model_dump_json(indent=2))
        return 0
    if action == "reject":
        if not task_id or not note:
            print("review reject requires REVIEW_ID and --note TEXT.", file=sys.stderr)
            return 1
        try:
            review = coordinator.reject(task_id, actor=actor or reviewer, finding=note)
        except (KeyError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(review.model_dump_json(indent=2))
        return 0
    print(f"Unknown review action: {action}", file=sys.stderr)
    return 1
