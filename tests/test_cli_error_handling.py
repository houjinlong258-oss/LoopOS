"""Tests for CLI error handling — expected user errors must not traceback."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run_cli(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "loopos.cli.app", *args],
        cwd=cwd or str(Path.cwd()),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )


def test_run_with_missing_workspace_returns_clean_error() -> None:
    result = _run_cli(
        "run",
        "demo",
        "--dry-run",
        "--workspace",
        "/this/path/does/not/exist/anywhere",
    )
    assert result.returncode != 0
    assert result.returncode == 2
    assert "workspace does not exist" in result.stderr
    assert "Traceback" not in result.stderr
    assert "Suggestion" in result.stderr


def test_run_with_file_as_workspace_returns_clean_error(tmp_path: Path) -> None:
    file_path = tmp_path / "not_a_dir.txt"
    file_path.write_text("hello", encoding="utf-8")
    # Sanity-check the file is visible from the parent process before
    # we hand the path to a subprocess. On Windows the file system
    # cache can briefly hide a freshly-created file from a child
    # process; this assertion ensures we never hand the subprocess
    # a path that *we* cannot see.
    assert file_path.exists()
    assert file_path.is_file()
    result = _run_cli("run", "demo", "--dry-run", "--workspace", str(file_path))
    assert result.returncode == 2
    assert "workspace is not a directory" in result.stderr
    assert "Traceback" not in result.stderr


def test_worktrees_plan_with_missing_workspace_returns_clean_error() -> None:
    result = _run_cli(
        "worktrees",
        "plan",
        "task-123",
        "--workspace",
        "/this/path/does/not/exist/anywhere",
    )
    assert result.returncode == 2
    assert "workspace does not exist" in result.stderr
    assert "Traceback" not in result.stderr
