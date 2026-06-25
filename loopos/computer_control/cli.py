"""CLI helpers for ``loopos computer ...``."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from loopos.computer_control.models import (
    ComputerControlPermissionSet,
    ComputerTask,
)
from loopos.computer_control.recorder import ComputerTraceRecorder
from loopos.computer_control.replay import ComputerReplay
from loopos.computer_control.session import ComputerController, backend_from_id


def computer_command(
    action: str = "run",
    task: str | None = None,
    *,
    backend: str = "fake",
    allow_computer_control: bool = False,
    approve_each_action: bool = False,
    sandbox: bool = False,
    dry_run: bool = True,
    latest: bool = False,
    data_dir: str = ".loopos",
    json_output: bool = True,
) -> int:
    root = Path(data_dir) / "computer_traces"
    recorder = ComputerTraceRecorder(root)
    if action == "replay":
        trace = recorder.load_latest() if latest else recorder.load_latest()
        result = ComputerReplay().replay(trace)
        return _emit(result.model_dump(mode="json"), json_output)
    if action != "run":
        print(f"unknown computer action: {action}", file=sys.stderr)
        return 2
    mode = "dry_run" if dry_run else ("sandbox_control" if sandbox else "local_control")
    controller = ComputerController(backend_from_id(backend))
    trace = controller.run_task(
        ComputerTask(description=task or "Observe fake desktop", expected_result="recorded"),
        mode=mode,  # type: ignore[arg-type]
        permissions=ComputerControlPermissionSet(
            allow_computer_control=allow_computer_control,
            approve_each_action=approve_each_action,
        ),
    )
    path = recorder.save(trace)
    payload = trace.model_dump(mode="json")
    payload["trace_path"] = str(path)
    payload["checkpoints"] = [c.model_dump(mode="json") for c in controller.checkpoints]
    payload["lail_signals"] = controller.lail_signals
    return _emit(payload, json_output)


def _emit(payload: dict[str, object], json_output: bool) -> int:
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload)
    return 0


__all__ = ["computer_command"]
