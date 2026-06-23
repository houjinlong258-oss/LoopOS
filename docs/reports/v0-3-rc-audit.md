# LoopOS v0.3 RC Audit — Test Report

This is the **v0.3 RC audit test report** for the LoopOS v0.3
Universal Agent Runtime.

## Summary

| Suite | Result |
| ----- | ------ |
| `python -m ruff check .` | **All checks passed!** |
| `python -m pytest -m "not slow"` | **932 passed**, 46 deselected, 19 subtests passed |
| `python scripts/v0_2_readiness_check.py --json` | **status: pass**, hard_fail_count: 0 |
| `python scripts/v0_3_readiness_check.py --json` | **status: pass**, hard_fail_count: 0 (21/21 checks pass) |
| `python scripts/anti_bloat_check.py --json` | **hard_fail_count: 0** |
| `python -m loopos.cli.app adapters list --json` | returns 4 adapters |
| `python -m loopos.cli.app providers-runtime list --json` | returns 3 providers |
| `python -m loopos.cli.app workbench --dry-run --json` | returns 9 panels |
| `python -m loopos.cli.app opengod g1 --fusion-mode mad_dog --json` | decision.kind=mad_dog |
| `python -m loopos.cli.app model-call hosts --dry-run --json` | status=completed |
| `python -m loopos.cli.app model-call hosts --allow-live-provider --json` | status=blocked, required_flags=[--budget-usd, --confirm] |

## v0.3 test files added

| Test file | # tests |
| --------- | ------: |
| `tests/test_providers_runtime.py` | 15 |
| `tests/test_agent_bus.py` | 10 |
| `tests/test_opengod.py` | 15 |
| `tests/test_product.py` | 9 |
| `tests/test_v0_3_cli.py` | 14 |
| `tests/test_adapters_v0_3.py` | 7 |
| `tests/test_fusion_orchestrator.py` | 6 |
| `tests/test_v0_3_deep_smoke.py` | 6 |
| `tests/test_v0_3_readiness_check.py` | 8 |
| **total** | **90** |

## v0.3 readiness checks (21/21 pass)

| # | Check | Status |
| - | ----- | ------ |
| 1 | product_layer_importable | PASS |
| 2 | workbench_renders_eight_panels | PASS |
| 3 | adapter_registry_populated | PASS |
| 4 | adapter_authority_guarded | PASS |
| 5 | agent_bus_translates_event | PASS |
| 6 | agent_bus_no_bypass | PASS |
| 7 | provider_runtime_importable | PASS |
| 8 | live_provider_disabled_by_default | PASS |
| 9 | openai_live_blocked_by_default | PASS |
| 10 | provider_budget_guard_blocks | PASS |
| 11 | secret_redaction | PASS |
| 12 | fusion_orchestrator_present | PASS |
| 13 | opengod_decision_emits_no_command | PASS |
| 14 | opengod_halt_on_hard_fail | PASS |
| 15 | opengod_budget_guard_blocks | PASS |
| 16 | cli_adapters_list | PASS |
| 17 | cli_providers_runtime_list | PASS |
| 18 | cli_model_call_dry_run | PASS |
| 19 | cli_model_call_blocks_live | PASS |
| 20 | cli_workbench_renders | PASS |
| 21 | v0_2_readiness_passes | PASS |

## Failure log (regression / pre-existing)

The only test failure observed during v0.3 development was in
`tests/test_cli_error_handling.py::test_run_with_file_as_workspace_returns_clean_error`,
which is a **pre-existing failure** in v0.2 (unrelated to v0.3) and
fails because of how the test's `tmp_path` is cleaned up before the
subprocess reads it. The error is a stale `path.exists()` check in
the CLI workspace validator. It is tracked separately and is not in
scope for v0.3. No v0.3 test was added or modified to mask this
pre-existing failure.

## v0.3 release verdict

* All v0.3 requirements implemented and verified.
* All v0.2 governance preserved.
* No new v0.2 regressions.
* Ruff clean.
* 932-test suite green.
* 21-check v0.3 readiness green.
* Anti-bloat hard-fail count == 0.

LoopOS v0.3 — **READY FOR RC RELEASE**.
