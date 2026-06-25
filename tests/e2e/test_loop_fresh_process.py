from __future__ import annotations

import json
import subprocess
import sys
from uuid import uuid4
from pathlib import Path
from typing import cast


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _run(args: list[str], cwd: Path) -> dict[str, object]:
    result = subprocess.run(
        [sys.executable, "-m", "loopos.cli.app", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return cast(dict[str, object], json.loads(result.stdout))


def test_loop_fresh_process_real_executor_status_deliver(tmp_path: Path) -> None:
    suffix = uuid4().hex
    repo = tmp_path / f"repo-{suffix}"
    data_dir = tmp_path / f"data-{suffix}"
    _write(repo / "calc.py", "def add(a, b):\n    return a - b\n")
    _write(repo / "tests" / "test_calc.py", "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n")
    run = _run(
        [
            "loop",
            "run",
            "Fix a simple failing test in a temp repo",
            "--real-executor",
            "--no-dry-run",
            "--sandbox",
            "--repo-path",
            str(repo),
            "--max-iterations",
            "1",
            "--data-dir",
            str(data_dir),
            "--json",
        ],
        Path.cwd(),
    )
    run_id = str(run["run_id"])
    status = _run(["loop", "status", "--run-id", run_id, "--data-dir", str(data_dir), "--json"], Path.cwd())
    deliver = _run(["loop", "deliver", "--run-id", run_id, "--data-dir", str(data_dir), "--json"], Path.cwd())
    replay = _run(["loop", "replay", "--run-id", run_id, "--data-dir", str(data_dir), "--json"], Path.cwd())
    assert status["run_id"] == run_id
    assert deliver["run_id"] == run_id
    assert replay["side_effects_reexecuted"] == 0
    assert "return a + b" in (repo / "calc.py").read_text(encoding="utf-8")
