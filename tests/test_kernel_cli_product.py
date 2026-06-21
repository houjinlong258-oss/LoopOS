from __future__ import annotations

import json
from pathlib import Path

from loopos.cli.commands.kernel_cli import kernel_command
from loopos.kernel import RunManager, RunRecord, RunSpec, TraceStore
from loopos.kernel.checkpoint import CheckpointStore, KernelCheckpoint


def _create_run(data_dir: Path) -> RunRecord:
    run = RunRecord.from_spec(RunSpec(goal="inspect the kernel", mode="dry_run"))
    run.status = "waiting_approval"
    run.phase = "WAITING_APPROVAL"
    run.step = 2
    RunManager(data_dir / "runs").save(run)
    trace = TraceStore(data_dir / "events.jsonl")
    trace.append("goal", run.run_id, 0, {"summary": run.goal})
    trace.append("instruction", run.run_id, 1, {"op": "GOAL.SET"})
    trace.append("policy", run.run_id, 1, {"reason_code": "test.allow"})
    CheckpointStore(data_dir / "checkpoints").save(KernelCheckpoint.from_run(run))
    return run


def test_kernel_inspect_json_shows_process_and_checkpoint(
    tmp_path: Path, capsys: object
) -> None:
    run = _create_run(tmp_path)
    assert kernel_command("inspect", run.run_id, data_dir=tmp_path, json_output=True) == 0
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.out)
    assert payload["run"]["status"] == "waiting_approval"
    assert payload["run"]["mode"] == "dry_run"
    assert payload["checkpoint"]["step"] == 2
    assert payload["replay_mode"] == "dry_replay_no_syscalls"


def test_trace_tree_groups_events_without_execution(tmp_path: Path, capsys: object) -> None:
    run = _create_run(tmp_path)
    assert kernel_command("trace-tree", run.run_id, data_dir=tmp_path, json_output=True) == 0
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.out)
    assert payload["mode"] == "trace_only_no_syscalls"
    assert [step["step"] for step in payload["steps"]] == [0, 1]
    assert payload["steps"][1]["nodes"][0]["summary"] == "GOAL.SET"
