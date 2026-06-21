"""Deep-smoke selection, timing, and timeout contracts."""

from __future__ import annotations

import sys
from pathlib import Path

import loopos.release.deep_smoke as deep_smoke


def test_deep_smoke_only_and_skip_report_durations() -> None:
    report = deep_smoke.run_deep_smoke(
        ".",
        only={"policy_remote_pipe", "fusion_trace"},
        skip={"fusion_trace"},
        timeout_per_check=20,
    )
    assert report["passed"] is True
    assert report["timeout_per_check"] == 20
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
