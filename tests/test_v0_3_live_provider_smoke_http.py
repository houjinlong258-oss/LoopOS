"""Tests for the loopback live-provider HTTP smoke.

The smoke script itself is exercised by
``scripts/v0_3_readiness_check.py::check_loopback_http_smoke`` and
also by ``tests/test_v0_3_live_provider_smoke_http.py``. These
tests assert the smoke's report shape and the script's exit code.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "v0_3_live_provider_smoke_http.py"


def _run_smoke(*, run: bool) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if run:
        env["LOOPOS_LIVE_HTTP_SMOKE"] = "1"
    return subprocess.run(
        [sys.executable, str(SMOKE_SCRIPT), "--json", *(["--run"] if run else [])],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(REPO_ROOT),
        env=env,
    )


def test_smoke_script_exists() -> None:
    assert SMOKE_SCRIPT.exists()


def test_smoke_gated_off_returns_pass_with_warning() -> None:
    """Without ``--run`` or the env var, the smoke emits a
    structured pass with a warning, not a hard fail.
    """
    env = os.environ.copy()
    env.pop("LOOPOS_LIVE_HTTP_SMOKE", None)
    result = subprocess.run(
        [sys.executable, str(SMOKE_SCRIPT), "--json"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(REPO_ROOT),
        env=env,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    assert payload["hard_fail_count"] == 0
    assert payload["checks"][0]["name"] == "loopback_http_smoke_gated"
    assert payload["checks"][0]["status"] is True
    assert payload["transport"] == "real_http_via_loopback"


def test_smoke_run_passes_all_five_invariants() -> None:
    """With ``--run`` and the env var, the smoke runs the loopback
    HTTP path and asserts all five invariants.
    """
    result = _run_smoke(run=True)
    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    assert payload["hard_fail_count"] == 0
    assert payload["transport"] == "real_http_via_loopback"
    names = [c["name"] for c in payload["checks"]]
    assert names == [
        "dry_run_keeps_server_quiet",
        "missing_key_blocks_structured",
        "real_http_client_path",
        "response_metadata_returned",
        "secrets_redacted_in_trace",
    ]
    # 3 of the 5 checks issue a real HTTP call; the other 2 do not
    # reach the server (dry-run, missing-key path).
    assert payload["request_hit_count"] == 3
    for c in payload["checks"]:
        assert c["status"] is True, f"{c['name']} failed: {c['detail']}"


def test_smoke_via_env_var_only() -> None:
    """Setting ``LOOPOS_LIVE_HTTP_SMOKE=1`` without ``--run`` should
    also enable the smoke path (the script reads the env var).
    """
    env = os.environ.copy()
    env["LOOPOS_LIVE_HTTP_SMOKE"] = "1"
    result = subprocess.run(
        [sys.executable, str(SMOKE_SCRIPT), "--json"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(REPO_ROOT),
        env=env,
    )
    assert result.returncode == 0, f"stderr={result.stderr!r}"
    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    assert payload["hard_fail_count"] == 0
    assert any(c["name"] == "real_http_client_path" for c in payload["checks"])


def test_smoke_does_not_leak_real_key_in_persisted_state() -> None:
    """Defense-in-depth: the smoke must not put the real key
    anywhere in its JSON report.
    """
    real_key = "sk-test-this-must-never-appear-in-report-1234567890"
    env = os.environ.copy()
    env["LOOPOS_LIVE_HTTP_SMOKE"] = "1"
    env["LOOPOS_SMOKE_TEST_KEY"] = real_key
    result = subprocess.run(
        [sys.executable, str(SMOKE_SCRIPT), "--json"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(REPO_ROOT),
        env=env,
    )
    # The smoke does not read ``LOOPOS_SMOKE_TEST_KEY``; this test
    # just makes sure the report is clean even when an unrelated
    # env var with a sensitive shape is present.
    assert real_key not in result.stdout
    assert real_key not in result.stderr


def test_readiness_check_picks_up_loopback_smoke() -> None:
    """The v0.3 readiness check must report the loopback smoke as
    passing when its env gate is set.
    """
    env = os.environ.copy()
    env["LOOPOS_LIVE_HTTP_SMOKE"] = "1"
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "v0_3_readiness_check.py"), "--json"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO_ROOT),
        env=env,
    )
    payload = json.loads(result.stdout)
    assert "loopback_http_smoke" in payload["checks"]
    check = payload["checks"]["loopback_http_smoke"]
    assert check["status"] is True, check["detail"]
    assert payload["status"] == "pass"