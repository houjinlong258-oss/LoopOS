"""CLI commands for System Kernel inspection.

Subcommands:
    loopos kernel inspect <run_id>
    loopos kernel invariants <run_id>
    loopos kernel lifecycle
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from loopos.cli.context import data_paths
from loopos.kernel.checkpoint import CheckpointStore
from loopos.kernel.invariants import KernelInvariantChecker
from loopos.kernel.lifecycle import KernelLifecycle
from loopos.kernel.run_manager import RunManager
from loopos.kernel.trace import TraceStore


def kernel_command(
    action: str = "inspect",
    run_id: str | None = None,
    *,
    data_dir: str | Path = ".loopos",
    json_output: bool = False,
) -> int:
    """Entry point for ``loopos kernel <action>``."""

    if action == "lifecycle":
        return _lifecycle(json_output=json_output)
    if action not in ("inspect", "invariants", "trace-tree"):
        print(f"Unknown kernel action: {action}", file=sys.stderr)
        return 1
    if not run_id:
        print(f"kernel {action} requires RUN_ID.", file=sys.stderr)
        return 1
    if action == "inspect":
        return _inspect(run_id, data_dir=data_dir, json_output=json_output)
    if action == "trace-tree":
        return _trace_tree(run_id, data_dir=data_dir, json_output=json_output)
    return _invariants(run_id, data_dir=data_dir, json_output=json_output)


def _inspect(run_id: str, *, data_dir: str | Path, json_output: bool) -> int:
    paths = data_paths(data_dir)
    store = TraceStore(Path(paths["events"]))
    events = store.list(run_id)
    try:
        run = RunManager(paths["runs"]).load(run_id)
    except FileNotFoundError:
        run = None
    if not events and run is None:
        print(f"no events for run: {run_id}", file=sys.stderr)
        return 1
    checkpoint = CheckpointStore(paths["checkpoints"]).latest(run_id)
    kinds: dict[str, int] = {}
    for event in events:
        key = event.kind or event.type or "unknown"
        kinds[key] = kinds.get(key, 0) + 1
    payload = {
        "run": run.model_dump(mode="json") if run else None,
        "event_count": len(events),
        "event_kinds": kinds,
        "checkpoint": checkpoint.model_dump(mode="json") if checkpoint else None,
        "replay_mode": "dry_replay_no_syscalls",
    }
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Run:        {run_id}")
        if run:
            print(f"Status:     {run.status}")
            print(f"Phase:      {run.phase}")
            print(f"Step:       {run.step}/{run.max_steps}")
            print(f"Mode:       {run.mode}")
            print(f"Approval:   {'pending' if run.pending_approval else 'none'}")
        print(f"Checkpoint: {checkpoint.checkpoint_id if checkpoint else 'none'}")
        print(f"Events:     {len(events)}")
        print("Kinds:")
        for kind, count in sorted(kinds.items()):
            print(f"  {kind}: {count}")
    return 0


def _invariants(run_id: str, *, data_dir: str | Path, json_output: bool) -> int:
    paths = data_paths(data_dir)
    store = TraceStore(Path(paths["events"]))
    events = store.list(run_id)
    if not events:
        print(f"no events for run: {run_id}", file=sys.stderr)
        return 1
    checker = KernelInvariantChecker()
    grouped: dict[int, list[dict[str, Any]]] = {}
    for event in events:
        grouped.setdefault(event.step, []).append(
            {
                "id": event.id,
                "kind": event.kind or event.type or "",
                "payload": event.payload,
            }
        )
    violations: list[dict[str, Any]] = []
    for step, step_events in sorted(grouped.items()):
        violations.extend(
            v.model_dump(mode="json")
            for v in checker.check_all(run_id, step, step_events)
        )
        violations.extend(
            v.model_dump(mode="json")
            for v in checker.check_approval_resume(run_id, step, step_events)
        )
    blocker_count = sum(item["severity"] == "blocker" for item in violations)
    warning_count = len(violations) - blocker_count
    payload = {
        "run_id": run_id,
        "status": "passed" if not violations else "failed" if blocker_count else "warning",
        "passed": 1 if not violations else 0,
        "warnings": warning_count,
        "failed": blocker_count,
        "violations": violations,
    }
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if not violations:
            print(f"Run {run_id}: all invariants satisfied.")
        else:
            print(f"Run {run_id}: {len(violations)} invariant violation(s).")
            for v in violations:
                print(
                    f"  [{v['severity']}] {v['invariant_id']} (step {v['step']}): {v['message']}"
                )
    return 0


def _trace_tree(run_id: str, *, data_dir: str | Path, json_output: bool) -> int:
    paths = data_paths(data_dir)
    events = TraceStore(paths["events"]).list(run_id)
    if not events:
        print(f"no events for run: {run_id}", file=sys.stderr)
        return 1
    steps: list[dict[str, Any]] = []
    for step in sorted({event.step for event in events}):
        nodes = []
        for event in (item for item in events if item.step == step):
            summary = (
                event.payload.get("op")
                or event.payload.get("reason_code")
                or event.payload.get("status")
                or event.payload.get("summary")
                or event.type
                or event.kind
            )
            nodes.append(
                {
                    "event_id": event.id,
                    "kind": event.kind,
                    "summary": str(summary),
                    "policy_decision_id": event.policy_decision_id,
                    "syscall_id": event.syscall_id,
                }
            )
        steps.append({"step": step, "nodes": nodes})
    payload = {
        "run_id": run_id,
        "mode": "trace_only_no_syscalls",
        "steps": steps,
    }
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    print(f"Trace tree: {run_id}")
    print("Mode: trace only; no syscalls executed")
    for step_group in steps:
        print(f"+- step {step_group['step']}")
        for node in step_group["nodes"]:  # type: ignore[union-attr]
            print(f"   +- {node['kind']}: {node['summary']}")
    return 0


def _lifecycle(*, json_output: bool) -> int:
    lifecycle = KernelLifecycle()
    lifecycle.transition("booting", reason="cli inspect")
    lifecycle.transition("ready", reason="cli ready")
    if json_output:
        print(json.dumps([e.model_dump(mode="json") for e in lifecycle.history], ensure_ascii=False, indent=2))
    else:
        print(f"Phase: {lifecycle.phase}")
        for event in lifecycle.history:
            print(f"  {event.phase}: {event.reason}")
    return 0
