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
from loopos.kernel.invariants import KernelInvariantChecker
from loopos.kernel.lifecycle import KernelLifecycle
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
    if action not in ("inspect", "invariants"):
        print(f"Unknown kernel action: {action}", file=sys.stderr)
        return 1
    if not run_id:
        print(f"kernel {action} requires RUN_ID.", file=sys.stderr)
        return 1
    if action == "inspect":
        return _inspect(run_id, data_dir=data_dir, json_output=json_output)
    return _invariants(run_id, data_dir=data_dir, json_output=json_output)


def _inspect(run_id: str, *, data_dir: str | Path, json_output: bool) -> int:
    paths = data_paths(data_dir)
    store = TraceStore(Path(paths["events"]))
    events = store.list(run_id)
    if not events:
        print(f"no events for run: {run_id}", file=sys.stderr)
        return 1
    if json_output:
        print(json.dumps([e.model_dump(mode="json") for e in events], ensure_ascii=False, indent=2))
    else:
        print(f"Run:        {run_id}")
        print(f"Events:     {len(events)}")
        kinds: dict[str, int] = {}
        for event in events:
            key = event.kind or event.type or "unknown"
            kinds[key] = kinds.get(key, 0) + 1
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
    if json_output:
        print(json.dumps(violations, ensure_ascii=False, indent=2))
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
