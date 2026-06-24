"""Tests for the v0.3 CLI commands."""

from __future__ import annotations

import contextlib
import io
import json
import os

from loopos.cli.commands import (
    adapters_command,
    model_call_command,
    opengod_command,
    providers_runtime_command,
    readiness_command,
    session_command,
    workbench_command,
)


from typing import Any


def _capture(func: Any, *args: Any, **kwargs: Any) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = func(*args, **kwargs)
    return rc, buf.getvalue()


def test_cli_adapters_list_json() -> None:
    rc, out = _capture(adapters_command, "list", json_output=True)
    assert rc == 0
    rows = json.loads(out)
    assert isinstance(rows, list)
    ids = {r["adapter_id"] for r in rows}
    assert "mock" in ids
    assert "hermes" in ids


def test_cli_adapters_inspect_known() -> None:
    rc, out = _capture(adapters_command, "inspect", "mock", json_output=True)
    assert rc == 0
    payload = json.loads(out)
    assert payload["adapter_id"] == "mock"


def test_cli_adapters_inspect_unknown_returns_error() -> None:
    rc, out = _capture(adapters_command, "inspect", "does-not-exist", json_output=True)
    assert rc == 1
    payload = json.loads(out)
    assert payload["status"] == "error"
    assert payload["error_code"] == "adapter_not_found"


def test_cli_adapters_test_dry_run() -> None:
    rc, out = _capture(adapters_command, "test", "mock", json_output=True)
    assert rc == 0
    payload = json.loads(out)
    assert payload["adapter_id"] == "mock"
    assert isinstance(payload["events"], list)
    assert len(payload["events"]) > 0


def test_cli_providers_runtime_list_json() -> None:
    rc, out = _capture(providers_runtime_command, "list", json_output=True)
    assert rc == 0
    rows = json.loads(out)
    ids = {r["provider_id"] for r in rows}
    assert "mock" in ids
    assert "openai" in ids
    assert "ollama" in ids


def test_cli_providers_runtime_test_mock() -> None:
    rc, out = _capture(
        providers_runtime_command, "test", "mock", model="mock-model", dry_run=True, json_output=True
    )
    assert rc == 0
    payload = json.loads(out)
    assert payload["status"] in ("completed", "dry_run")


def test_cli_model_call_dry_run() -> None:
    rc, out = _capture(
        model_call_command,
        os.devnull,
        provider="mock",
        model="mock-model",
        dry_run=True,
        json_output=True,
    )
    assert rc == 0
    payload = json.loads(out)
    assert payload["status"] in ("completed", "dry_run")


def test_cli_model_call_live_blocks_without_budget() -> None:
    """When actually going live (dry_run=False) without budget+confirm,
    the command must block. The three flags are only required on the
    live path, not on the dry-run path."""
    rc, out = _capture(
        model_call_command,
        r"C:\Windows\System32\drivers\etc\hosts",
        provider="openai",
        model="gpt-4.1",
        dry_run=False,
        allow_live_provider=True,
        budget_usd=0.0,
        confirm=False,
        json_output=True,
    )
    assert rc == 4
    payload = json.loads(out)
    assert payload["status"] == "blocked"
    assert "live_provider_requires_explicit_approval" in payload["reason_codes"]
    assert "--budget-usd" in payload["required_flags"]
    assert "--confirm" in payload["required_flags"]


def test_cli_opengod_decide_mad_dog() -> None:
    rc, out = _capture(
        opengod_command,
        "g1",
        fusion_mode="mad_dog",
        fusion_score=80,
        json_output=True,
    )
    assert rc == 0
    payload = json.loads(out)
    assert payload["decision"]["kind"] == "mad_dog"
    assert payload["verdict"]["status"] == "ok"


def test_cli_opengod_hard_fail_halts() -> None:
    rc, out = _capture(
        opengod_command, "g1", hard_fail_count=2, json_output=True
    )
    assert rc == 0
    payload = json.loads(out)
    assert payload["decision"]["kind"] == "halt"


def test_cli_workbench_dry_run_json() -> None:
    rc, out = _capture(
        workbench_command, None, dry_run=True, json_output=True
    )
    assert rc == 0
    payload = json.loads(out)
    assert payload["status"] == "ok"
    panels = payload["panels"]
    assert all(k in panels for k in (
        "goal", "agent", "policy", "aci", "ali", "trace_replay", "fusion", "readiness"
    ))


def test_cli_workbench_dry_run_plain() -> None:
    rc, out = _capture(
        workbench_command, None, dry_run=True, json_output=False
    )
    assert rc == 0
    assert "goal" in out
    assert "agent" in out
    assert "policy" in out
    assert "aci" in out
    assert "readiness" in out


def test_cli_session_list_empty() -> None:
    rc, out = _capture(session_command, "list", data_dir=".loopos-test-empty", json_output=True)
    assert rc == 0
    payload = json.loads(out)
    assert payload == []


def test_cli_readiness_check_json() -> None:
    rc, out = _capture(readiness_command, "check", json_output=True)
    # rc may be 0 (pass) or 1 (fail); both are valid outcomes for the
    # readiness check; we just want the JSON to parse.
    payload = json.loads(out)
    assert "status" in payload
    assert "hard_fail_count" in payload
