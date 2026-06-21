"""Producer, verifier, and reviewer CLI commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from loopos.cli.context import data_paths
from loopos.cli.renderers import render_review_artifact_text, render_review_gate_text
from loopos.kernel import RunManager, TraceStore
from loopos.maintainability.analyzer import MaintainabilityAnalyzer
from loopos.maintainability.diff_summary import parse_diff
from loopos.maintainability.gate import MaintainabilityGate
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
    diff_file: str | Path | None = None,
    human_output: bool = False,
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
            diff_file=diff_file,
            human_output=human_output,
        )
    if action == "gate":
        return _gate(
            run_id,
            data_dir=data_dir,
            high_risk=high_risk,
            maintainability_blocked=maintainability_blocked,
            producer=producer,
            reviewer=reviewer,
            human_output=human_output,
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
    diff_file: str | Path | None,
    human_output: bool,
) -> int:
    if not run_id:
        print("review artifact requires --run-id RUN_ID.", file=sys.stderr)
        return 1
    builder = ReviewArtifactBuilder(run_id, task_id=task_id)
    builder.set_roles(producer=producer, verifier=verifier, reviewer=reviewer)
    paths = data_paths(data_dir)
    try:
        run = RunManager(paths["runs"]).load(run_id)
    except FileNotFoundError:
        print(f"run not found: {run_id}", file=sys.stderr)
        return 1
    events = TraceStore(paths["events"]).list(run_id)
    builder.set_trace_events([event.id for event in events])
    builder.set_acceptance(
        {
            "goal": (
                "passed"
                if run.status == "succeeded"
                else "failed"
                if run.is_terminal
                else "unknown"
            )
        }
    )
    for event in events:
        event_type = _event_type(event)
        if event_type in {"policy_check", "POLICY.CHECK"} or event.kind == "policy":
            builder.add_policy_check(dict(event.payload))
        elif event_type in {"data_guard_result", "DATA_GUARD.RESULT"}:
            builder.add_data_guard_check(
                {
                    "target": event.payload.get("target", event.payload.get("name", "database")),
                    "passed": bool(event.payload.get("passed", event.payload.get("success", True))),
                    "event_id": event.id,
                    "event_type": event_type,
                }
            )
        elif event.kind == "syscall" and _contains_database_action(event.payload):
            builder.add_data_guard_check(
                {
                    "target": event.payload.get("name", "database"),
                    "passed": bool(event.payload.get("success", True)),
                    "event_id": event.id,
                    "event_type": event_type,
                }
            )
        elif event_type in {"test_result", "TEST.RESULT"}:
            builder.add_test_result(
                {
                    "event_id": event.id,
                    "passed": bool(event.payload.get("passed", event.payload.get("success", False))),
                    "summary": event.payload.get("summary", "test result"),
                    "event_type": event_type,
                }
            )
        elif event.kind == "observation" and _contains_test_result(event.payload):
            builder.add_test_result(
                {
                    "event_id": event.id,
                    "passed": bool(event.payload.get("success", False)),
                    "summary": event.payload.get("summary", "test observation"),
                    "event_type": event_type,
                }
            )
    if diff_file is not None:
        path = Path(diff_file)
        if not path.is_file():
            print(f"diff file not found: {path}", file=sys.stderr)
            return 1
        diff_text = path.read_text(encoding="utf-8")
        summary = parse_diff(diff_text, run_id=run_id)
        report = MaintainabilityAnalyzer().analyze(
            summary, files=_extract_added_files(diff_text)
        )
        gate = MaintainabilityGate().evaluate(report)
        builder.set_diff_summary(summary.model_dump(mode="json"))
        builder.set_maintainability_evidence(
            report.model_dump(mode="json"), gate.model_dump(mode="json")
        )
        for required_action in gate.required_actions:
            builder.add_required_change(required_action)
    artifact = builder.build()
    _save_artifact(artifact, data_dir)
    payload = artifact.model_dump(mode="json")
    if human_output:
        print(render_review_artifact_text(payload))
    else:
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
    human_output: bool,
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
    payload = decision.model_dump(mode="json")
    if human_output:
        print(render_review_gate_text(payload))
    else:
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


def _extract_added_files(diff_text: str) -> dict[str, str]:
    files: dict[str, list[str]] = {}
    current: str | None = None
    unparsed: list[str] = []
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            files.setdefault(current, [])
        elif line.startswith("+") and not line.startswith("+++"):
            if current is not None:
                files[current].append(line[1:])
            else:
                unparsed.append(line[1:])
    if unparsed:
        files.setdefault("__unparsed_diff__.py", []).extend(unparsed)
    return {path: "\n".join(lines) for path, lines in files.items()}


def _event_type(event: Any) -> str:
    value = getattr(event, "type", None) or ""
    payload = getattr(event, "payload", {}) or {}
    return str(payload.get("event_type") or value)


def _contains_database_action(payload: dict[str, Any]) -> bool:
    return "database." in json.dumps(payload, ensure_ascii=False).lower()


def _contains_test_result(payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=False).lower()
    return "pytest" in text or "unittest" in text
