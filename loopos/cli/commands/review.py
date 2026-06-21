"""Producer, verifier, and reviewer CLI commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from loopos.cli.context import data_paths
from loopos.review import ReviewCoordinator, ReviewStore
from loopos.review.artifact import ReviewArtifact
from loopos.review.gate import MergeGate, ReviewArtifactBuilder
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
    run_id: str | None = None,
    high_risk: bool = False,
    maintainability_blocked: bool = False,
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
    if action == "artifact":
        return _artifact(
            run_id,
            task_id,
            data_dir=data_dir,
            producer=producer,
            verifier=verifier,
            reviewer=reviewer,
        )
    if action == "gate":
        return _gate(
            run_id,
            data_dir=data_dir,
            high_risk=high_risk,
            maintainability_blocked=maintainability_blocked,
            producer=producer,
            reviewer=reviewer,
        )
    print(f"Unknown review action: {action}", file=sys.stderr)
    return 1


def _artifact(
    run_id: str | None,
    task_id: str | None,
    *,
    data_dir: str | Path,
    producer: str,
    verifier: str,
    reviewer: str,
) -> int:
    if not run_id:
        print("review artifact requires --run-id RUN_ID.", file=sys.stderr)
        return 1
    builder = ReviewArtifactBuilder(run_id, task_id=task_id)
    builder.set_roles(producer=producer, verifier=verifier, reviewer=reviewer)
    artifact = builder.build()
    _save_artifact(artifact, data_dir)
    print(artifact.model_dump_json(indent=2))
    return 0


def _gate(
    run_id: str | None,
    *,
    data_dir: str | Path,
    high_risk: bool,
    maintainability_blocked: bool,
    producer: str,
    reviewer: str,
) -> int:
    if not run_id:
        print("review gate requires --run-id RUN_ID.", file=sys.stderr)
        return 1
    artifact = _load_artifact(run_id, data_dir)
    if artifact is None:
        print(f"no review artifact found for run: {run_id}", file=sys.stderr)
        return 1
    gate = MergeGate()
    producer_is_reviewer = bool(producer) and producer == reviewer
    decision = gate.evaluate(
        artifact,
        maintainability_blocked=maintainability_blocked,
        high_risk=high_risk,
        producer_is_reviewer=producer_is_reviewer,
    )
    print(decision.model_dump_json(indent=2))
    return 0


def _artifact_path(data_dir: str | Path) -> Path:
    base = Path(data_dir)
    base.mkdir(parents=True, exist_ok=True)
    return base / "review_artifacts.json"


def _save_artifact(artifact: ReviewArtifact, data_dir: str | Path) -> None:
    path = _artifact_path(data_dir)
    artifacts: dict[str, dict[str, Any]] = {}
    if path.exists():
        try:
            rows = json.loads(path.read_text(encoding="utf-8") or "[]")
            artifacts = {row["run_id"]: row for row in rows if "run_id" in row}
        except (json.JSONDecodeError, KeyError):
            artifacts = {}
    artifacts[artifact.run_id] = artifact.model_dump(mode="json")
    path.write_text(
        json.dumps(list(artifacts.values()), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _load_artifact(run_id: str, data_dir: str | Path) -> ReviewArtifact | None:
    path = _artifact_path(data_dir)
    if not path.exists():
        return None
    try:
        rows = json.loads(path.read_text(encoding="utf-8") or "[]")
    except json.JSONDecodeError:
        return None
    for row in rows:
        if row.get("run_id") == run_id:
            return ReviewArtifact.model_validate(row)
    return None
