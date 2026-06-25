from __future__ import annotations

import json
import subprocess
import sys
from uuid import uuid4
from pathlib import Path
from typing import cast


def _run(args: list[str]) -> dict[str, object]:
    result = subprocess.run(
        [sys.executable, "-m", "loopos.cli.app", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return cast(dict[str, object], json.loads(result.stdout))


def test_computer_control_fresh_process_replay_does_not_execute(tmp_path: Path) -> None:
    data_dir = tmp_path / f"data-{uuid4().hex}"
    run = _run([
        "computer",
        "run",
        "Observe fake desktop and verify target",
        "--backend",
        "fake",
        "--allow-computer-control",
        "--sandbox",
        "--no-dry-run",
        "--data-dir",
        str(data_dir),
        "--json",
    ])
    replay = _run(["computer", "replay", "--latest", "--data-dir", str(data_dir), "--json"])
    assert run["backend"] == "fake"
    assert replay["actions_reexecuted"] == 0
    assert replay["actions_replayed"] == 1
