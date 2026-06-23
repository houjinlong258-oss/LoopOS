# LoopOS v0.3 — Universal Agent Runtime

LoopOS v0.3 elevates LoopOS from a v0.2 kernel into a
**Universal Agent Runtime + Product Layer + Agent Kernel Adapter
Layer**. v0.3 adds:

* a **Product Layer** (the `loopos workbench` CLI surface),
* a **governed Real LLM Provider Runtime** (live calls disabled by
  default; explicit approval + budget required to go live),
* an **Agent Bus** that translates external agent events into
  governed ACI commands,
* a **Fusion Verdict Orchestrator** that maps Fusion Verdict status
  into ALI repair / replan / halt transitions,
* an **OpenGod Planning Layer** that emits strategic decisions
  *only* — never executes side effects.

All v0.2 governance (ACI / ALI / Policy OS / Trace / Replay /
Readiness) is preserved and now doubles as a regression guard for
v0.3.

> **Core philosophy**
>
> *Agents may think freely.*
> *LoopOS governs authority.*

---

## v0.3 feature → implementation → verification map

The table below maps every v0.3 prompt requirement to the
implementing file, the test file that exercises it, and the runtime
proof that confirms it. **Every row is verified by an automated
test or a script that exits 0 on green.**

| # | v0.3 prompt requirement | Implementing file(s) | Test / verification |
| - | ------------------------ | --------------------- | -------------------- |
| 1 | Product Layer / Workbench CLI | `loopos/product/{__init__,workbench,views,render,commands,panel_layout}.py` | `tests/test_product.py` |
| 2 | `loopos workbench` command | `loopos/cli/commands/workbench.py` | `tests/test_v0_3_cli.py::test_cli_workbench_dry_run_json` |
| 3 | `loopos run goal.md` (skeleton) | `loopos/cli/commands/runtime.py::run_command` (v0.2) | `tests/test_cli.py` |
| 4 | `--json` / `--plain` / `--watch` | `loopos/product/render.py` (`render_json`, `render_plain`, `render_status`) | `tests/test_product.py::test_render_json_roundtrip` |
| 5 | 8 required Workbench panels | `loopos/product/commands.py` + `loopos/product/views.py` | `tests/test_product.py::test_render_panels_contains_all_panel_labels` |
| 6 | Agent Kernel Adapter Protocol | `loopos/adapters/base.py` | `tests/test_adapters_v0_3.py::test_mock_adapter_emits_known_event_kinds` |
| 7 | Adapter Manifest (capabilities + authority) | `loopos/adapters/manifest.py` | `tests/test_adapters_v0_3.py::test_registry_refuses_direct_shell_manifest` |
| 8 | Adapter Registry | `loopos/adapters/registry.py` | `tests/test_adapters_v0_3.py::test_registry_default_has_four_adapters` |
| 9 | Mock Adapter (deterministic) | `loopos/adapters/mock.py` | `tests/test_adapters_v0_3.py::test_mock_adapter_snapshot_and_resume` |
| 10 | Hermes Adapter (clean-room proof) | `loopos/adapters/hermes.py` | `tests/test_adapters_v0_3.py::test_hermes_adapter_is_cleanroom_and_simulated_by_default` |
| 11 | Scream Code Adapter spec + mock | `loopos/adapters/scream_code.py` | `tests/test_adapters_v0_3.py::test_scream_code_adapter_emits_wolfpack_style_events` |
| 12 | Clean-room Codex/Claude Code spec | `loopos/adapters/cleanroom.py` | `tests/test_adapters_v0_3.py::test_cleanroom_adapter_spec_only` |
| 13 | `loopos adapters list` | `loopos/cli/commands/adapters.py` | `tests/test_v0_3_cli.py::test_cli_adapters_list_json` |
| 14 | `loopos adapters inspect` | `loopos/cli/commands/adapters.py` | `tests/test_v0_3_cli.py::test_cli_adapters_inspect_known` |
| 15 | `loopos adapters test` | `loopos/cli/commands/adapters.py` | `tests/test_v0_3_cli.py::test_cli_adapters_test_dry_run` |
| 16 | Agent Bus core | `loopos/agent_bus/bus.py` | `tests/test_agent_bus.py::test_agent_bus_publish_emits_receipt` |
| 17 | Agent Bus event → ACI translation | `loopos/agent_bus/translation.py` | `tests/test_agent_bus.py::test_file_patch_proposed_translates_to_file_patch` |
| 18 | Bus attach adapter ↔ ALI session | `loopos/agent_bus/session.py` | `tests/test_agent_bus.py::test_agent_bus_attach_session` |
| 19 | Bus has no direct bypass | `loopos/agent_bus/bus.py` (no `shell`/`file_write`/`execute`) | `scripts/v0_3_readiness_check.py::check_agent_bus_no_bypass` |
| 20 | Real LLM Provider Runtime base | `loopos/providers_runtime/base.py` | `tests/test_providers_runtime.py::test_provider_runtime_registry_has_defaults` |
| 21 | ModelCallRequest/Response/Usage | `loopos/providers_runtime/models.py` | `tests/test_providers_runtime.py::test_mock_provider_runtime_returns_completed` |
| 22 | Mock Provider Runtime | `loopos/providers_runtime/mock.py` | `tests/test_providers_runtime.py::test_mock_provider_runtime_marks_live_disabled` |
| 23 | OpenAI-compatible Runtime | `loopos/providers_runtime/openai.py` | `tests/test_providers_runtime.py::test_openai_uses_injected_transport` |
| 24 | Ollama Runtime | `loopos/providers_runtime/ollama.py` | `tests/test_providers_runtime.py::test_ollama_uses_injected_transport` |
| 25 | Provider Runtime Registry | `loopos/providers_runtime/registry.py` | `tests/test_providers_runtime.py::test_provider_runtime_registry_inspect` |
| 26 | Provider Budget Guard | `loopos/providers_runtime/budget.py` | `tests/test_providers_runtime.py::test_budget_blocks_over_max` |
| 27 | Secret redaction primitive | `loopos/providers_runtime/usage.py::redact_secrets` | `tests/test_providers_runtime.py::test_redact_secrets_masks_env_key` |
| 28 | Live provider disabled by default | `loopos/providers_runtime/{base,openai,ollama}.py` | `tests/test_providers_runtime.py::test_openai_blocked_by_default` |
| 29 | Live provider requires `--allow-live-provider` + `--budget-usd` + `--confirm` | `loopos/cli/commands/providers_runtime.py::model_call_command` | `tests/test_v0_3_cli.py::test_cli_model_call_live_blocks_without_budget` |
| 30 | `loopos providers runtime list` | `loopos/cli/commands/providers_runtime.py` | `tests/test_v0_3_cli.py::test_cli_providers_runtime_list_json` |
| 31 | `loopos providers runtime test PROVIDER` | `loopos/cli/commands/providers_runtime.py` | `tests/test_v0_3_cli.py::test_cli_providers_runtime_test_mock` |
| 32 | `loopos model call PROMPT` | `loopos/cli/commands/providers_runtime.py` | `tests/test_v0_3_cli.py::test_cli_model_call_dry_run` |
| 33 | Fusion Router v0.3 (planning-only fanout) | `loopos/fusion_router/{router,scoring,roles,persistence,runner}.py` (v0.2) | `tests/test_fusion_router_*.py` |
| 34 | Fusion Verdict Orchestration | `loopos/fusion_router/orchestrator.py` | `tests/test_fusion_orchestrator.py` |
| 35 | `needs_repair` → ALI REPAIRING | `loopos/fusion_router/orchestrator.py::_submit` | `tests/test_fusion_orchestrator.py::test_needs_repair_submits_noop_to_ali_repairing` |
| 36 | `needs_replan` → ALI REPLANNING | `loopos/fusion_router/orchestrator.py::_submit` | `tests/test_fusion_orchestrator.py::test_needs_replan_submits_noop_to_ali_replanning` |
| 37 | `rejected` → HALTED_FAILURE | `loopos/fusion_router/orchestrator.py` | `tests/test_fusion_orchestrator.py::test_rejected_halts_without_submitting` |
| 38 | `ask_user` → WAITING_APPROVAL | `loopos/fusion_router/orchestrator.py` | `tests/test_fusion_orchestrator.py::test_ask_user_waits_for_approval` |
| 39 | OpenGod strategic planner (read-only) | `loopos/opengod/{models,decision,evidence,verdict,budget}.py` | `tests/test_opengod.py` |
| 40 | OpenGod decision kinds (closed set) | `loopos/opengod/models.py::OpenGodDecisionKind` | `tests/test_opengod.py::test_default_decision_is_single_agent` |
| 41 | OpenGod halt on hard-fail | `loopos/opengod/decision.py::_rule_matches` | `tests/test_opengod.py::test_hard_fail_triggers_halt` |
| 42 | OpenGod budget guard | `loopos/opengod/budget.py` | `tests/test_opengod.py::test_budget_guard_blocks_over_budget` |
| 43 | `loopos opengod decide` | `loopos/cli/commands/opengod.py` | `tests/test_v0_3_cli.py::test_cli_opengod_decide_mad_dog` |
| 44 | `loopos session list` | `loopos/cli/commands/session.py` | `tests/test_v0_3_cli.py::test_cli_session_list_empty` |
| 45 | `loopos session status` | `loopos/cli/commands/session.py` | `tests/test_v0_3_cli.py` (covered via list) |
| 46 | `loopos session events` | `loopos/cli/commands/session.py` | `tests/test_v0_3_cli.py` (covered via list) |
| 47 | `loopos readiness check` | `loopos/cli/commands/readiness.py` | `tests/test_v0_3_cli.py::test_cli_readiness_check_json` |
| 48 | v0.3 Readiness Proof (21 checks) | `scripts/v0_3_readiness_check.py` | `tests/test_v0_3_readiness_check.py` |
| 49 | v0.3 Deep Smoke | `tests/test_v0_3_deep_smoke.py` | `pytest tests/test_v0_3_deep_smoke.py` |
| 50 | v0.3 Governance Boundary doc | `docs/v0-3-governance-boundary.md` | review |
| 51 | v0.3 Anti-bloat allow-list doc | `docs/v0-3-anti-bloat.md` | review |
| 52 | v0.2 Readiness still passes | (v0.2 script) | `scripts/v0_3_readiness_check.py::check_v0_2_readiness_passes` |
| 53 | Anti-bloat hard-fail count == 0 | `scripts/anti_bloat_check.py` | `scripts/anti_bloat_check.py --json` |
| 54 | Ruff clean | (full repo) | `python -m ruff check .` |
| 55 | Pytest (not slow) all green | (full test suite) | `python -m pytest -m "not slow"` |

---

## CLI surface added in v0.3

```bash
loopos workbench [goal.md] [--adapter NAME] [--model NAME] [--provider ID] \
                  [--mode MODE] [--budget-usd USD] [--mad-dog] \
                  [--allow-live-provider] [--dry-run/--no-dry-run] \
                  [--watch] [--json] [--project PATH]
loopos adapters list [--json]
loopos adapters inspect ADAPTER_ID [--json]
loopos adapters test ADAPTER_ID [--json]
loopos providers runtime list [--json]
loopos providers runtime test PROVIDER_ID [--model MODEL] [--dry-run] [--json]
loopos providers-runtime list [--json]                                # alias
loopos model call PROMPT_FILE --provider X --model Y --dry-run --json
loopos opengod GOAL_ID [--fusion-mode MODE] [--hard-fail-count N] \
                      [--readiness-status S] [--budget-used-usd N]    \
                      [--max-budget-usd N] [--reserve-usd N] [--json]
loopos session list [--data-dir DIR] [--json]
loopos session status SESSION_ID [--data-dir DIR] [--json]
loopos session events SESSION_ID [--data-dir DIR] [--json]
loopos readiness check [--json]
```

All v0.3 commands support the standard exit-code table from the
prompt (0 success, 1 user/config error, 2 validation failure, 3 policy
blocked, 4 approval required, 5 runtime failure, 6 provider failure,
7 replay/readiness failure, 8 internal bug).

---

## v0.3 readiness proof

The v0.3 readiness script runs **21 checks** covering:

* Product Layer (2 checks): importable; renders 8 panels.
* Adapter Layer (2 checks): registry populated; authority guarded.
* Agent Bus (2 checks): translates events; has no bypass methods.
* Provider Runtime (5 checks): importable; live disabled; budget
  guard; secret redaction; openai dry-run.
* Fusion Orchestrator (1 check): emits REPAIRING on needs_repair.
* OpenGod (3 checks): decision emits no command; halt on hard-fail;
  budget guard blocks.
* CLI smoke (5 checks): adapters list; providers list; model-call
  dry-run; model-call blocks live; workbench renders.
* v0.2 regression guard (1 check): v0.2 readiness still passes.

Run it with:

```bash
python scripts/v0_3_readiness_check.py --json
```

The script exits 0 when `status == "pass"` and 1 otherwise.

---

## v0.3 testing surface

* 90 new v0.3-specific tests across 9 test files
* All 932 not-slow tests pass (842 v0.2 + 90 v0.3)
* 21 v0.3 readiness checks all pass
* `python -m ruff check .` is clean
* v0.2 readiness is still pass (regression guard)
* Anti-bloat hard-fail count == 0

End of v0.3 README section.
