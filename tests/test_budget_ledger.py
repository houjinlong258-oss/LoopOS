"""Tests for the shared ``BudgetLedger``.

These tests are the P0-1 acceptance gate. They prove:

* repeated live calls accumulate spend;
* the Workbench and CLI paths share one accounting path and cannot
  double-spend;
* dry-run never commits spend;
* failed calls do not commit spend;
* the ledger is scoped by ``(provider_id, model_id, session_id)``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from loopos.providers_runtime import (
    BudgetLedger,
    ModelCallRequest,
    MockProviderRuntime,
    get_default_ledger,
    reset_default_ledger,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_default_ledger() -> Any:
    """Reset the process-wide ledger before AND after each test."""
    reset_default_ledger()
    yield
    reset_default_ledger()


# ---------------------------------------------------------------------------
# Core ledger mechanics
# ---------------------------------------------------------------------------


def test_ledger_make_key_normalises_case_and_whitespace() -> None:
    led = BudgetLedger()
    k1 = led.make_key("  OpenAI  ", "GPT-4.1", "sess-1")
    k2 = led.make_key("openai", "gpt-4.1", "sess-1")
    assert k1 == k2


def test_ledger_make_key_normalises_session_id() -> None:
    led = BudgetLedger()
    assert led.make_key("p", "m", "") == led.make_key("p", "m", None)
    assert led.make_key("p", "m", "  ") == led.make_key("p", "m", None)


def test_ledger_get_or_create_is_idempotent() -> None:
    led = BudgetLedger()
    b1 = led.get_or_create("openai", "gpt-4.1", None, max_usd=1.0)
    b2 = led.get_or_create("openai", "gpt-4.1", None, max_usd=99.0)
    # Second call must not overwrite the first.
    assert b1 is b2
    assert b1.max_usd == 1.0
    assert b2.max_usd == 1.0


def test_ledger_repeated_calls_accumulate_spend() -> None:
    led = BudgetLedger()
    led.get_or_create("openai", "gpt-4.1", None, max_usd=10.0)
    for _ in range(3):
        led.get_or_create("openai", "gpt-4.1", None, max_usd=99.0)
        led.check("openai", "gpt-4.1", None, 0.01, approved=True)
        led.commit("openai", "gpt-4.1", None, 0.01)
    snap = led.snapshot()
    key = led.make_key("openai", "gpt-4.1", None)
    assert snap[key]["used_usd"] == pytest.approx(0.03)
    assert snap[key]["used_requests"] == 3


def test_ledger_blocks_over_max() -> None:
    led = BudgetLedger()
    led.get_or_create("openai", "gpt-4.1", None, max_usd=0.05)
    decision = led.check("openai", "gpt-4.1", None, 1.00, approved=True)
    assert not decision.allowed
    assert "provider_budget_exceeded" in decision.reason_codes


def test_ledger_check_without_entry_is_allowed_noop() -> None:
    """Without an entry, the ledger does not silently block. The
    caller opted out of budget tracking; spend is not recorded.
    """
    led = BudgetLedger()
    decision = led.check("openai", "gpt-4.1", None, 1.0, approved=True)
    assert decision.allowed
    assert decision.used_usd == 0.0


def test_ledger_commit_without_entry_is_noop() -> None:
    led = BudgetLedger()
    # No prior get_or_create -> commit returns False, no entry created.
    assert led.commit("openai", "gpt-4.1", None, 0.5) is False
    assert led.snapshot() == {}


# ---------------------------------------------------------------------------
# Cross-path accounting (Workbench + CLI share one ledger)
# ---------------------------------------------------------------------------


def test_workbench_and_cli_share_ledger_no_double_spend(tmp_path: Path) -> None:
    """The Workbench and ``model_call_command`` must both land on
    the *same* ledger entry, so cumulative spend is counted once
    across both paths.
    """
    from loopos.cli.commands.providers_runtime import model_call_command
    from loopos.product import Workbench

    wb = Workbench()
    led = get_default_ledger()
    led.get_or_create("mock", "mock-model", None, max_usd=10.0)

    # Path 1: Workbench issues a "live" call. Mock provider returns
    # ``dry_run`` by default, so we must explicitly set
    # ``live_provider_calls_allowed=True`` and let the Workbench route
    # the request. To do this without mocking, we use the ledger's
    # commit hook directly to simulate a real Workbench spend.
    led.check("mock", "mock-model", None, 0.01, approved=True)
    led.commit("mock", "mock-model", None, 0.01)

    # Path 2: CLI path. Same key -> same entry.
    led.check("mock", "mock-model", None, 0.01, approved=True)
    led.commit("mock", "mock-model", None, 0.01)

    key = led.make_key("mock", "mock-model", None)
    snap = led.snapshot()
    assert snap[key]["used_usd"] == pytest.approx(0.02)
    assert snap[key]["used_requests"] == 2

    # Now actually exercise ``model_call_command`` with a tiny budget
    # so the live gate fires. The mock provider returns
    # ``dry_run`` unless ``live_provider_calls_allowed=True``, so we
    # must enable the live flag too. With both flags set, the
    # ledger records one more spend.
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("hi", encoding="utf-8")
    rc = model_call_command(
        str(prompt_path),
        provider="mock",
        model="mock-model",
        dry_run=False,
        allow_live_provider=True,
        budget_usd=10.0,
        confirm=True,
        json_output=True,
    )
    assert rc == 0
    snap = led.snapshot()
    assert snap[key]["used_usd"] == pytest.approx(0.03)
    assert snap[key]["used_requests"] == 3

    # Now: the Workbench, called with a matching live setup, must
    # land on the same key and the same budget instance.
    wb_result = wb.call_model(
        provider_id="mock",
        model_id="mock-model",
        prompt="from workbench",
        budget_max_usd=10.0,
        allow_live=True,
        dry_run=False,
    )
    assert wb_result["status"] == "completed"
    snap = led.snapshot()
    assert snap[key]["used_usd"] == pytest.approx(0.04)
    assert snap[key]["used_requests"] == 4


# ---------------------------------------------------------------------------
# Dry-run and failure do not commit
# ---------------------------------------------------------------------------


def test_workbench_dry_run_does_not_commit() -> None:
    from loopos.product import Workbench

    wb = Workbench()
    led = get_default_ledger()
    # Pre-create the entry so the dry-run has somewhere to NOT commit.
    led.get_or_create("mock", "mock-model", None, max_usd=10.0)
    key = led.make_key("mock", "mock-model", None)

    snap_before = led.snapshot()[key]

    # Dry-run path: ``allow_live=True`` is overridden by
    # ``dry_run=True`` inside ``call_model``. The Mock runtime
    # always returns ``status="completed"`` because it is
    # in-process, but the ledger must NOT see the spend.
    result = wb.call_model(
        provider_id="mock",
        model_id="mock-model",
        prompt="hi",
        budget_max_usd=10.0,
        allow_live=True,
        dry_run=True,  # dry-run path
    )
    assert result["status"] == "completed"
    snap_after = led.snapshot()[key]
    assert snap_after == snap_before
    assert snap_after["used_usd"] == 0.0
    assert snap_after["used_requests"] == 0


def test_workbench_failed_call_does_not_commit() -> None:
    """A failed live call must not commit spend. This is the
    invariant that prevents paying for an unsuccessful request.
    """
    from loopos.providers_runtime import ProviderRuntimeRegistry
    from loopos.product import Workbench

    wb = Workbench()
    led = get_default_ledger()
    led.get_or_create("failing", "failing-model", None, max_usd=10.0)
    key = led.make_key("failing", "failing-model", None)

    # Build a registry with a single runtime that always fails.
    class _FailingRuntime(MockProviderRuntime):
        provider_id = "failing"

        def call(self, request: ModelCallRequest) -> Any:
            from loopos.providers_runtime.models import ModelCallResponse

            return ModelCallResponse(
                request_id=request.request_id,
                provider_id=self.provider_id,
                model_id=request.model_id,
                status="failed",
                content=None,
                reason_codes=["simulated_failure"],
            )

    new_registry = ProviderRuntimeRegistry(register_defaults=False)
    new_registry.register(_FailingRuntime())
    wb.provider_registry = new_registry

    result = wb.call_model(
        provider_id="failing",
        model_id="failing-model",
        prompt="hi",
        budget_max_usd=10.0,
        allow_live=True,
        dry_run=False,
    )

    assert result["status"] == "failed"
    snap_after = led.snapshot()
    # Entry must exist (we created it) but no commit must have happened.
    assert key in snap_after
    assert snap_after[key]["used_usd"] == 0.0
    assert snap_after[key]["used_requests"] == 0


# ---------------------------------------------------------------------------
# Ledger scoping: provider / model / session
# ---------------------------------------------------------------------------


def test_ledger_scopes_by_provider() -> None:
    led = BudgetLedger()
    led.get_or_create("openai", "gpt-4.1", None, max_usd=1.0)
    led.get_or_create("ollama", "llama3", None, max_usd=99.0)
    led.check("openai", "gpt-4.1", None, 0.5, approved=True)
    led.commit("openai", "gpt-4.1", None, 0.5)
    snap = led.snapshot()
    openai_key = led.make_key("openai", "gpt-4.1", None)
    ollama_key = led.make_key("ollama", "llama3", None)
    assert snap[openai_key]["used_usd"] == pytest.approx(0.5)
    assert snap[ollama_key]["used_usd"] == 0.0


def test_ledger_scopes_by_model() -> None:
    led = BudgetLedger()
    led.get_or_create("openai", "gpt-4.1", None, max_usd=1.0)
    led.get_or_create("openai", "gpt-4.1-mini", None, max_usd=99.0)
    led.check("openai", "gpt-4.1", None, 0.5, approved=True)
    led.commit("openai", "gpt-4.1", None, 0.5)
    snap = led.snapshot()
    big_key = led.make_key("openai", "gpt-4.1", None)
    mini_key = led.make_key("openai", "gpt-4.1-mini", None)
    assert snap[big_key]["used_usd"] == pytest.approx(0.5)
    assert snap[mini_key]["used_usd"] == 0.0


def test_ledger_scopes_by_session_id() -> None:
    led = BudgetLedger()
    led.get_or_create("openai", "gpt-4.1", "session-A", max_usd=10.0)
    led.get_or_create("openai", "gpt-4.1", "session-B", max_usd=10.0)
    led.check("openai", "gpt-4.1", "session-A", 0.5, approved=True)
    led.commit("openai", "gpt-4.1", "session-A", 0.5)
    snap = led.snapshot()
    a_key = led.make_key("openai", "gpt-4.1", "session-A")
    b_key = led.make_key("openai", "gpt-4.1", "session-B")
    assert snap[a_key]["used_usd"] == pytest.approx(0.5)
    assert snap[b_key]["used_usd"] == 0.0


def test_ledger_session_id_empty_is_same_as_none() -> None:
    led = BudgetLedger()
    b1 = led.get_or_create("openai", "gpt-4.1", "", max_usd=1.0)
    b2 = led.get_or_create("openai", "gpt-4.1", None, max_usd=99.0)
    assert b1 is b2


def test_ledger_process_default_is_singleton() -> None:
    a = get_default_ledger()
    b = get_default_ledger()
    assert a is b


def test_ledger_reset_clears_all_entries() -> None:
    led = BudgetLedger()
    led.get_or_create("openai", "gpt-4.1", None, max_usd=1.0)
    led.commit("openai", "gpt-4.1", None, 0.1)
    assert led.snapshot()
    led.reset()
    assert led.snapshot() == {}


def test_ledger_is_thread_safe() -> None:
    """Smoke test: concurrent commits do not lose updates.

    10 threads * 100 commits of 0.01 USD each = 10.0 USD total.
    The lock must serialise commits.
    """
    import threading

    led = BudgetLedger()
    led.get_or_create("openai", "gpt-4.1", None, max_usd=100.0)
    key = led.make_key("openai", "gpt-4.1", None)

    def worker() -> None:
        for _ in range(100):
            led.check("openai", "gpt-4.1", None, 0.01, approved=True)
            led.commit("openai", "gpt-4.1", None, 0.01)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    snap = led.snapshot()
    assert snap[key]["used_usd"] == pytest.approx(10.0)
    assert snap[key]["used_requests"] == 1000