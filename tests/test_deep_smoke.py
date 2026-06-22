"""Deep-smoke selection, timing, and timeout contracts."""

from __future__ import annotations

import sys
import json
import subprocess
from pathlib import Path

import loopos.release.deep_smoke as deep_smoke


def test_deep_smoke_only_and_skip_report_durations() -> None:
    report = deep_smoke.run_deep_smoke(
        ".",
        only={"policy_remote_pipe", "fusion_trace"},
        skip={"fusion_trace"},
        timeout_per_check=20,
        global_timeout=60,
    )
    assert report["passed"] is True
    assert report["timeout_per_check"] == 20
    assert report["global_timeout"] == 60
    assert len(report["checks"]) == 1
    check = report["checks"][0]
    assert check["name"] == "policy_remote_pipe"
    assert check["duration_ms"] >= 0
    assert "loopos.cli.app" in check["command"]


def test_deep_smoke_timeout_is_structured(tmp_path: Path) -> None:
    def slow_check() -> deep_smoke.SmokeCheck:
        result = deep_smoke._run(  # noqa: SLF001
            tmp_path,
            [sys.executable, "-c", "import time; time.sleep(5)"],
        )
        return deep_smoke.SmokeCheck(
            name="slow",
            status="passed" if result.returncode == 0 else "failed",
            message="slow local check",
        )

    check = deep_smoke._timed_check("slow", slow_check, 1)  # noqa: SLF001
    assert check.status == "failed"
    assert check.reason == "timeout"
    assert check.timeout_seconds == 1
    assert check.duration_ms < 2500
    assert "time.sleep(5)" in check.command


def test_deep_smoke_global_timeout_names_running_check() -> None:
    report = deep_smoke.run_deep_smoke(
        ".",
        only={"registry_examples"},
        timeout_per_check=20,
        global_timeout=1,
    )
    assert report["passed"] is False
    assert report["currently_running_check"] == "registry_examples"
    assert report["checks"][0]["reason"] == "global_timeout"
    assert report["duration_ms"] < 6000


def test_deep_smoke_jsonl_progress_keeps_json_stdout_clean() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "loopos.release.deep_smoke",
            "--only",
            "cli_help",
            "--json",
            "--jsonl-progress",
            "--global-timeout",
            "20",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    report = json.loads(result.stdout)
    progress = [json.loads(line) for line in result.stderr.splitlines() if line.strip()]
    assert result.returncode == 0
    assert report["passed"] is True
    assert [event["event"] for event in progress] == ["check_started", "check_completed"]
