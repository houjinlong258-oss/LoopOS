"""Tests for the webhook gateway demo flow (message -> run -> approval -> resume)."""

from __future__ import annotations

import subprocess
import sys
import tempfile
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


def test_webhook_flow_command_produces_all_steps() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = _run_cli(
            "gateway",
            "webhook-flow",
            "fix the failing pytest",
            "--user-id",
            "user-1",
            "--run-id",
            "run-demo",
            "--risk",
            "high",
            "--data-dir",
            str(Path(tmp) / "loopos"),
        )
    assert result.returncode == 0, result.stderr
    assert "step1_message" in result.stdout
    assert "step2_run_spec" in result.stdout
    assert "step3_approval_card" in result.stdout
    assert "step4_approval_response" in result.stdout
    assert "step5_resume_decision" in result.stdout
    assert "message -> run_spec -> approval -> resume" in result.stdout


def test_webhook_health_command() -> None:
    result = _run_cli("gateway", "webhook-health")
    assert result.returncode == 0
    assert "healthy" in result.stdout


def test_webhook_flow_rejects_unauthorized_user() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        # user-unknown is not in the allowlist
        result = _run_cli(
            "gateway",
            "webhook-flow",
            "fix the failing pytest",
            "--user-id",
            "user-unknown",
            "--run-id",
            "run-demo",
            "--data-dir",
            str(Path(tmp) / "loopos"),
        )
    assert result.returncode != 0
