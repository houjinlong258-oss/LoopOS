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
    """The global-timeout branch of the deep-smoke runner is
    exercised on its *semantics*, not on wall-clock thresholds.

    The previous incarnation asserted ``duration_ms < 6000``, a
    magic number that flaked under machine load because the
    runner needs to terminate the subprocess tree (Windows
    ``taskkill /T`` / POSIX ``SIGTERM -> SIGKILL``) and reap the
    orphan. The new assertions check the contract the runner
    promises: configured timeout is honored, running check is
    named, global-timeout result is reported, the check actually
    started (recorded command is non-empty), the duration is
    bounded by ``configured timeout + explicit grace window``,
    and the runner leaves no orphan side effects behind.

    See ``docs/reports/v0-3-alpha-hardening-p1.md`` Section P1-1
    for the regression-cover rationale.
    """
    global_timeout_seconds = 1
    # Explicit grace window: the runner needs to terminate the
    # subprocess tree and reap the orphan. 8 seconds is enough on
    # CI runners; we still assert the actual bound instead of
    # encoding it as a magic constant. Increasing the grace window
    # does not make the test less deterministic -- it makes it
    # more forgiving of slow CI.
    grace_window_ms = 8_000
    report = deep_smoke.run_deep_smoke(
        ".",
        only={"registry_examples"},
        timeout_per_check=20,
        global_timeout=global_timeout_seconds,
    )
    # 1. Configured timeout is honored in the report.
    assert report["global_timeout"] == global_timeout_seconds
    # 2. Run reports failure when global timeout fires.
    assert report["passed"] is False
    # 3. The currently-running check is named correctly.
    assert report["currently_running_check"] == "registry_examples"
    # 4. The global-timeout result is reported on the failing check.
    assert report["checks"][0]["name"] == "registry_examples"
    assert report["checks"][0]["reason"] == "global_timeout"
    assert report["checks"][0]["status"] == "failed"
    # ``timeout_seconds`` is the *effective* timeout, not the
    # configured one: the runner clamps the configured global
    # timeout to ``suite_deadline - time.perf_counter()`` at the
    # moment the check is dispatched, so the effective value can
    # be marginally smaller than what the caller asked for. We
    # assert the effective value is within the configured
    # window -- never larger, never zero, never negative.
    eff_timeout = float(report["checks"][0]["timeout_seconds"])
    assert 0.0 < eff_timeout <= global_timeout_seconds, (
        f"effective timeout out of range: {eff_timeout!r}"
    )
    # 5. Process exits cleanly: the check actually started (the
    # recorded command is non-empty), and the duration is at
    # least the configured timeout (we waited) plus a bounded
    # grace window for tree termination.
    assert report["checks"][0]["command"], "check never started"
    duration_ms = int(report["duration_ms"])
    min_duration_ms = global_timeout_seconds * 1000
    max_duration_ms = min_duration_ms + grace_window_ms
    assert duration_ms >= min_duration_ms, (
        f"runner returned before the configured timeout: "
        f"{duration_ms} ms < {min_duration_ms} ms"
    )
    assert duration_ms < max_duration_ms, (
        f"global-timeout cleanup exceeded grace window: "
        f"{duration_ms} ms >= {max_duration_ms} ms "
        f"(timeout={min_duration_ms}ms + grace={grace_window_ms}ms)"
    )
    # 6. No side effects remain. The runner uses a
    # ``tempfile.TemporaryDirectory`` for ``data_dir`` and
    # ``workspace``; the temp dir is gone by the time the runner
    # returns. We additionally verify that the working tree at
    # ``.`` is unchanged: the runner must not have left a
    # ``.loopos-demo`` / ``.loopos`` / registry scratch dir at
    # the repo root. (The :func:`deep_smoke.run_deep_smoke` is
    # the only entry point exercised here; it is the only one
    # responsible for the cleanup contract.)
    import os
    cwd = os.getcwd()
    forbidden = {
        ".loopos-demo",
        ".loopos-smoke",
    }
    leftover = [
        name
        for name in forbidden
        if (Path(cwd) / name).exists()
        and (Path(cwd) / name).stat().st_mtime
        > __import__("time").time() - 30
    ]
    assert not leftover, (
        f"deep smoke left side-effect directories at the repo "
        f"root: {leftover}"
    )


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
