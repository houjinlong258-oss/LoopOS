"""Tests for the v0.3 readiness check script.

These tests invoke the script as a subprocess so the same code path
that runs in CI is exercised here. The script must report
``status == "pass"`` and must not have any hard-failed checks.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "v0_3_readiness_check.py"


def _run() -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--json"],
        capture_output=True, text=True, timeout=60, cwd=str(REPO_ROOT),
    )
    assert result.returncode in (0, 1), f"unexpected exit code {result.returncode}"
    payload: dict[str, Any] = json.loads(result.stdout)
    return payload


def test_v0_3_readiness_status_pass() -> None:
    payload = _run()
    assert payload["status"] == "pass", (
        f"v0.3 readiness failed: "
        f"{[(n, c['detail']) for n, c in payload['checks'].items() if not c['status']]}"
    )
    assert payload["hard_fail_count"] == 0


def test_v0_3_readiness_schema_version() -> None:
    payload = _run()
    assert payload["schema_version"] == "0.3"
    assert "generated_at" in payload
    assert "checks" in payload


def test_v0_3_readiness_includes_product_proof() -> None:
    payload = _run()
    assert payload["checks"]["product_layer_importable"]["status"] is True
    assert payload["checks"]["workbench_renders_eight_panels"]["status"] is True


def test_v0_3_readiness_includes_adapter_proof() -> None:
    payload = _run()
    assert payload["checks"]["adapter_registry_populated"]["status"] is True
    assert payload["checks"]["adapter_authority_guarded"]["status"] is True


def test_v0_3_readiness_includes_provider_proof() -> None:
    payload = _run()
    assert payload["checks"]["provider_runtime_importable"]["status"] is True
    assert payload["checks"]["live_provider_disabled_by_default"]["status"] is True
    assert payload["checks"]["openai_live_blocked_by_default"]["status"] is True
    assert payload["checks"]["provider_budget_guard_blocks"]["status"] is True
    assert payload["checks"]["secret_redaction"]["status"] is True


def test_v0_3_readiness_includes_opengod_proof() -> None:
    payload = _run()
    assert payload["checks"]["opengod_decision_emits_no_command"]["status"] is True
    assert payload["checks"]["opengod_halt_on_hard_fail"]["status"] is True
    assert payload["checks"]["opengod_budget_guard_blocks"]["status"] is True


def test_v0_3_readiness_includes_cli_proof() -> None:
    payload = _run()
    assert payload["checks"]["cli_adapters_list"]["status"] is True
    assert payload["checks"]["cli_providers_runtime_list"]["status"] is True
    assert payload["checks"]["cli_model_call_dry_run"]["status"] is True
    assert payload["checks"]["cli_model_call_blocks_live"]["status"] is True
    assert payload["checks"]["cli_workbench_renders"]["status"] is True


def test_v0_3_readiness_includes_v0_2_regression_guard() -> None:
    payload = _run()
    assert payload["checks"]["v0_2_readiness_passes"]["status"] is True
