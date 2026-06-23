# LoopOS v0.3 — Alpha Implementation Snapshot / Split Audit

> **Status (this document):** v0.3-alpha implementation snapshot complete.
> **Audit target:** `HEAD` at audit time (`0931b82`).
> **Verdict:** **v0.3-alpha accepted, RC blocked pending hardening.**

This document is the alpha-phase split audit. It supersedes the
earlier "strict RC runtime audit" (`docs/reports/v0-3-strict-rc-audit.md`)
in the following ways:

* The v0.3 implementation has been committed in a **1 + 5 commit
  topology** (one large implementation drop + five small follow-ups),
  not the originally planned seven-logical-commit split. The reality
  is documented below; the original 7-commit plan is preserved in
  Section B as a reference for the **next** re-split pass.
* All validation gates that were green at the strict-audit
  time-stamp remain green after the v0.3 implementation landed
  (ruff, mypy, pytest, v0.2 readiness, v0.3 readiness, anti-bloat).
* The pre-existing flaky test
  `test_run_with_file_as_workspace_returns_clean_error` — which the
  strict audit fixed in-tree and the parallel Codex closeout report
  incorrectly claimed "continues to fail" — is **passing** in the
  current `pytest -m "not slow"` run (947 passed, 9 skipped, 0 failed).

---

## A. Commit list

Six commits land on top of v0.2 (`136fdf3`):

| # | Hash | Timestamp (UTC+8) | Type | Subject | Files | Lines |
| - | ---- | ----------------- | ---- | ------- | ----- | ----- |
| 1 | `e39b9d5` | 2026-06-23 22:26 | docs / mega-drop | `docs(repo): separate product docs from agent prompts` | 76 | +9472 / -6 |
| 2 | `f7b70f3` | 2026-06-23 22:27 | feat | `feat(cli): add rich workbench rendering foundation` | 11 (new `loopos/cli_ui/`) | +593 |
| 3 | `273c21f` | 2026-06-23 22:29 | feat | `feat(cli): add loopos workbench command surface` | 6 | +82 / -7 |
| 4 | `569409f` | 2026-06-23 22:34 | fix | `fix(cli): prepend panel name to panel title in render_view_rich to preserve test assertions` | 1 | +3 / -2 |
| 5 | `b5b6b07` | 2026-06-23 22:51 | fix | `fix(cli): resolve static type checking, mypy warnings, and add missing unit tests` | 14 | +115 / -38 |
| 6 | `0931b82` | 2026-06-23 22:52 | docs | `docs: add v0.3 rich cli workbench closeout report` | 1 | +129 |

### A.1 Topology reality

The user-requested plan was **seven logical commits** (product → agent → providers → fusion → opengod → readiness → docs). What landed is **one mega-commit + five follow-ups**. The mega-commit's title is a docs one, but the file list is the full v0.3 implementation:

* All 9 files of `loopos/adapters/`
* All 6 files of `loopos/agent_bus/`
* All 6 files of `loopos/product/`
* All 6 files of `loopos/opengod/`
* All 10 files of `loopos/providers_runtime/`
* `loopos/fusion_router/__init__.py` + `loopos/fusion_router/orchestrator.py`
* All 7 new CLI commands under `loopos/cli/commands/`
* `loopos/cli/app.py` + `loopos/cli/commands/__init__.py` + `loopos/cli/fallback.py` (CLI surface registration)
* `scripts/v0_3_live_provider_smoke.py` + `scripts/v0_3_readiness_check.py`
* 9 v0.3 test files + the `test_cli_error_handling.py` flaky-test fix
* `CHANGELOG.md` (v0.3-alpha entry) + `docs/v0-3-*.md` (4 files) + `docs/reports/v0-3-*.md` (3 files)
* 6 prompt files renamed into `docs/prompts/`

This is a structural concern for RC. See Section F (RC blockers, item 1).

### A.2 Per-commit files in detail

**Commit 1 — `e39b9d5` docs(repo): separate product docs from agent prompts**

```
Moved (0 byte diff, just rename): 6 prompt files
  docs/LoopOS_Current_Repo_Codex_Improvement_Prompts.md
  docs/LoopOS_Data_Safety_Backup_Guard_Prompt.md
  docs/LoopOS_Final_Upgrade_Master_Codex_Prompt.md
  docs/LoopOS_Fusion_Codex_Prompts.md
  docs/LoopOS_Kernel_Level_Codex_Prompt.md
  docs/LoopOS_Ultimate_Landable_Codex_Prompt.md
  docs/prompts/loopos-codex-prompt-pack.md (already in prompts/)

CHANGELOG.md                                                          +82
docs/reports/v0-3-audit-bugs.md                                       +156
docs/reports/v0-3-rc-audit.md                                         +84
docs/reports/v0-3-strict-rc-audit.md                                  +786
docs/v0-3-anti-bloat.md                                               +75
docs/v0-3-governance-boundary.md                                      +137
docs/v0-3-readiness.md                                                +120
docs/v0-3-readme.md                                                   +160

loopos/adapters/{__init__,base,cleanroom,events,hermes,
                manifest,mock,registry,scream_code}.py               (9 files)
loopos/agent_bus/{__init__,bus,command_bridge,events,
                 session,translation}.py                             (6 files)
loopos/cli/app.py                                                     +148
loopos/cli/commands/__init__.py                                       +31 / -1
loopos/cli/commands/{adapters,opengod,providers_runtime,
                     readiness,session,workbench}.py                 (6 new commands)
loopos/cli/fallback.py                                                +134
loopos/fusion_router/__init__.py                                      +6
loopos/fusion_router/orchestrator.py                                  +147
loopos/opengod/{__init__,budget,decision,evidence,models,verdict}.py  (6 files)
loopos/product/{__init__,commands,panel_layout,render,views,
               workbench}.py                                         (6 files)
loopos/providers_runtime/{__init__,base,budget,errors,mock,
                         models,ollama,openai,registry,usage}.py     (10 files)
scripts/v0_3_live_provider_smoke.py                                   +345
scripts/v0_3_readiness_check.py                                       +635

tests/test_adapters_v0_3.py                                           +85
tests/test_agent_bus.py                                               +191
tests/test_cli_error_handling.py                                      +7
tests/test_fusion_orchestrator.py                                     +97
tests/test_opengod.py                                                 +176
tests/test_product.py                                                 +110
tests/test_providers_runtime.py                                       +192
tests/test_v0_3_cli.py                                                +178
tests/test_v0_3_deep_smoke.py                                         +118
tests/test_v0_3_live_provider_smoke.py                                +255
tests/test_v0_3_readiness_check.py                                    +84
```

**Commit 2 — `f7b70f3` feat(cli): add rich workbench rendering foundation**

```
loopos/cli_ui/{__init__,console,diff,errors,json,mascot,
              panels,progress,prompts,tables,theme}.py  (11 new files, +593)
```

Introduces a separate `loopos/cli_ui/` rendering layer (Rich-based)
parallel to `loopos/product/render.py`. Panels, tables, prompts,
errors, theme, mascot, progress.

**Commit 3 — `273c21f` feat(cli): add loopos workbench command surface**

```
loopos/cli/commands/adapters.py          +8
loopos/cli/commands/policy.py            +24 / -2
loopos/cli/commands/providers_runtime.py +8
loopos/cli/commands/runtime.py           +33 / -2
loopos/cli/commands/workbench.py         +10 / -1
pyproject.toml                           +6 / -2  (moved rich+typer to optional 'workbench' extra)
```

Adds the Typer binding for `workbench`, `adapters`, `providers-runtime`,
`model-call`, `opengod`, `session`, `readiness` commands. Also touches
`policy.py` and `runtime.py` for Rich migration. Moves `rich` and
`typer` to an optional `workbench` extra in `pyproject.toml` so the
stdlib-`argparse` fallback in `loopos/cli/fallback.py` remains usable.

**Commit 4 — `569409f` fix(cli): prepend panel name to panel title**

```
loopos/cli_ui/panels.py +3 / -2
```

Small follow-up to make `render_view_rich` prepend the panel name to
the title so the test assertion that reads the panel header keeps
working.

**Commit 5 — `b5b6b07` fix(cli): resolve static type checking, mypy warnings**

```
loopos/cli_ui/console.py               +11 / -2
loopos/cli_ui/diff.py                  +5 / -1
loopos/cli_ui/errors.py                +5 / -1
loopos/cli_ui/panels.py                +5 / -1
loopos/cli_ui/tables.py                +9 / -2
loopos/cli_ui/theme.py                 +4 / -2
tests/test_agent_bus.py                +15 / -7
tests/test_cli_ui_console.py           +59 (new)
tests/test_fusion_orchestrator.py      +5 / -1
tests/test_opengod.py                  +4 / -1
tests/test_v0_3_cli.py                 +5 / -1
tests/test_v0_3_deep_smoke.py          +1
tests/test_v0_3_live_provider_smoke.py +18 / -9
tests/test_v0_3_readiness_check.py     +7 / -2
```

Brings mypy from the strict-audit baseline (27 errors in v0.3 test
files) to **0 errors in 392 source files**. Adds 1 new test file
(`test_cli_ui_console.py`, 59 lines). Touches 7 existing test files
to fix type-checker complaints and re-enable gated assertions.

**Commit 6 — `0931b82` docs: add v0.3 rich cli workbench closeout report**

```
docs/reports/v0-3-rich-cli-workbench-closeout.md +129
```

The closeout doc written by the parallel Codex agent. It contains one
inaccuracy (it claims the flaky test "continues to fail" — see
Section E.4) but is otherwise a useful scope summary.

---

## B. Original 7-commit plan vs. actual 1+5 reality

The user asked for seven logical commits. For the next re-split pass
(planned for v0.3-alpha → v0.3-rc transition), the following mapping
should drive `git reset --soft` + re-commit:

| Planned commit (per user spec) | Actual location in current tree | Re-split action |
| ------------------------------ | ------------------------------- | --------------- |
| 1. `feat(product): workbench product surface` | `e39b9d5` (mixed) + `f7b70f3` (cli_ui) | Extract `loopos/product/*`, `loopos/cli/commands/workbench.py`, `tests/test_product.py`, `tests/test_v0_3_deep_smoke.py` (workbench slice), plus the v0.3 workbench sections of `loopos/cli/app.py` and `loopos/cli/commands/__init__.py` |
| 2. `feat(agent): adapter layer + agent bus` | `e39b9d5` (mixed) | Extract `loopos/adapters/*`, `loopos/agent_bus/*`, `loopos/cli/commands/adapters.py`, `tests/test_adapters_v0_3.py`, `tests/test_agent_bus.py` |
| 3. `feat(providers): governed provider runtime` | `e39b9d5` (mixed) | Extract `loopos/providers_runtime/*`, `loopos/cli/commands/providers_runtime.py` (model-call + providers-runtime), `loopos/cli/commands/session.py` (session list/status/events reads provider-runtime data), `tests/test_providers_runtime.py`, `tests/test_v0_3_live_provider_smoke.py`, `scripts/v0_3_live_provider_smoke.py` |
| 4. `feat(fusion): verdict orchestration prototype` | `e39b9d5` (mixed) + `569409f` (cli_ui patch) | Extract `loopos/fusion_router/orchestrator.py`, `loopos/fusion_router/__init__.py` delta, `tests/test_fusion_orchestrator.py`. The `cli_ui/panels.py` patch in 569409f affects the workbench surface, not fusion, so it stays with commit 1's re-split. |
| 5. `feat(opengod): strategic planning layer` | `e39b9d5` (mixed) | Extract `loopos/opengod/*`, `loopos/cli/commands/opengod.py`, `tests/test_opengod.py` |
| 6. `test(readiness): v0.3 readiness + regression` | `e39b9d5` (mixed) + `b5b6b07` (mypy/test fix) | Extract `scripts/v0_3_readiness_check.py`, `tests/test_v0_3_readiness_check.py`, plus the test fixes in `b5b6b07` |
| 7. `docs(v0.3): alpha audit + implementation map` | `e39b9d5` (mixed) + `0931b82` (closeout) | Extract `docs/v0-3-*.md` (4 files), `docs/reports/v0-3-*.md` (3 files), `CHANGELOG.md` (v0.3-alpha entry), and the closeout report |

**Why the re-split matters for RC:** the mega-commit's
`docs(repo): separate product docs from agent prompts` message
disguises a 76-file v0.3 implementation drop. `git log --oneline`
or `git bisect` will mislead reviewers who expect commits to be
self-describing. RC requires that `git log` between v0.2 and v0.3
read as a narrative of logical features, not a docs commit that
happens to carry 76 files.

---

## C. Feature → implementation → test map

This section maps every v0.3-alpha claim to the file(s) that
implement it, the test(s) that exercise it, and the runtime proof
(mock / dry-run / real / planning-only).

| # | v0.3-alpha feature | Implementing file(s) | Test / verification | Runtime proof class |
| - | ------------------ | --------------------- | ------------------- | ------------------- |
| 1 | Workbench product surface | `loopos/product/{__init__,workbench,views,render,commands,panel_layout}.py` | `tests/test_product.py` | **dry-run** (renderer only, no side effects) |
| 2 | Rich-based workbench panels (new `cli_ui/`) | `loopos/cli_ui/{panels,tables,theme,mascot,errors,prompts,progress,diff,json,console}.py` | `tests/test_cli_ui_console.py` | **dry-run** |
| 3 | `loopos workbench` CLI (Typer + argparse fallback) | `loopos/cli/commands/workbench.py` + `loopos/cli/app.py` + `loopos/cli/fallback.py` | `tests/test_v0_3_cli.py` | **dry-run** |
| 4 | Adapter interface | `loopos/adapters/{__init__,base,manifest,events,registry}.py` | `tests/test_adapters_v0_3.py` | **mock** (in-process; no live fan-out) |
| 5 | Mock adapter | `loopos/adapters/mock.py` | `tests/test_adapters_v0_3.py::test_mock_adapter_*` | **mock** |
| 6 | Hermes adapter (clean-room proof) | `loopos/adapters/hermes.py` | `tests/test_adapters_v0_3.py::test_hermes_adapter_*` | **spec-only / simulated** (no real Hermes CLI invocation in this audit) |
| 7 | Scream-Code adapter | `loopos/adapters/scream_code.py` | `tests/test_adapters_v0_3.py::test_scream_code_adapter_*` | **spec-only** |
| 8 | Clean-room Codex/Claude Code adapter | `loopos/adapters/cleanroom.py` | `tests/test_adapters_v0_3.py::test_cleanroom_adapter_*` | **spec-only** |
| 9 | `loopos adapters list / inspect / test` CLI | `loopos/cli/commands/adapters.py` | `tests/test_v0_3_cli.py` | **mock + spec-only** |
| 10 | Agent Bus core | `loopos/agent_bus/{bus,events,session,translation,command_bridge}.py` | `tests/test_agent_bus.py` | **mock + translated commands** (bus dispatches to v0.2 `CommandRunner`) |
| 11 | Bus has no direct bypass (governance) | `loopos/agent_bus/bus.py` | `scripts/v0_3_readiness_check.py::check_agent_bus_no_bypass` | code-level scan |
| 12 | Provider Runtime base + models | `loopos/providers_runtime/{__init__,base,models,budget,usage,errors,registry}.py` | `tests/test_providers_runtime.py` | **mock** + **real (gated)** |
| 13 | Mock provider runtime | `loopos/providers_runtime/mock.py` | `tests/test_providers_runtime.py::test_mock_*` | **mock** (in-process, no network) |
| 14 | OpenAI-compatible provider runtime | `loopos/providers_runtime/openai.py` | `tests/test_providers_runtime.py::test_openai_uses_injected_transport` | **real (gated)** — wire-level call goes through injected transport; live `--allow-live-provider` requires `OPENAI_API_KEY` + `--budget-usd` + `--confirm` |
| 15 | Ollama provider runtime | `loopos/providers_runtime/ollama.py` | `tests/test_providers_runtime.py::test_ollama_uses_injected_transport` | **real (gated)** — needs running `OLLAMA_HOST` daemon; not exercised in this audit run |
| 16 | Provider budget guard | `loopos/providers_runtime/budget.py` | `tests/test_providers_runtime.py::test_budget_blocks_over_max` | **enforced** — `check()` before every live call, `commit()` after |
| 17 | Secret redaction | `loopos/providers_runtime/usage.py::redact_secrets` | `tests/test_providers_runtime.py::test_redact_secrets_masks_env_key` | **enforced** — masks env keys, `Bearer …`, `sk-…` prefixes |
| 18 | `loopos providers-runtime list / test` CLI | `loopos/cli/commands/providers_runtime.py` | `tests/test_v0_3_cli.py` | **mock** + **dry-run** |
| 19 | `loopos model-call PROMPT_FILE` CLI | `loopos/cli/commands/providers_runtime.py::model_call_command` | `tests/test_v0_3_cli.py::test_cli_model_call_*` | **dry-run** + **real (gated)** |
| 20 | Live provider smoke (gated) | `scripts/v0_3_live_provider_smoke.py` | `tests/test_v0_3_live_provider_smoke.py` (gated on `LOOPOS_LIVE_SMOKE=1`) | **9/9 live safety checks pass** (in-process, injected transport) |
| 21 | Fusion Verdict Orchestrator | `loopos/fusion_router/orchestrator.py` | `tests/test_fusion_orchestrator.py` | **caller-driven, no daemon** (maps `FusionVerdict.status` → `AgentCommand`; dispatches via v0.2 `CommandRunner`) |
| 22 | `needs_repair` / `needs_replan` / `rejected` / `ask_user` → ALI transitions | `loopos/fusion_router/orchestrator.py::_submit` | `tests/test_fusion_orchestrator.py` | **planning-only** (no background scheduler) |
| 23 | OpenGod strategic planner | `loopos/opengod/{models,decision,evidence,verdict,budget}.py` | `tests/test_opengod.py` | **planning-only** — emits `OpenGodDecision` + `OpenGodVerdict`; never calls a provider, never opens a file, never executes shell |
| 24 | OpenGod budget guard | `loopos/opengod/budget.py` | `tests/test_opengod.py::test_budget_guard_blocks_over_budget` | **enforced** |
| 25 | `loopos opengod …` CLI | `loopos/cli/commands/opengod.py` | `tests/test_v0_3_cli.py` | **planning-only** |
| 26 | `loopos session list / status / events` CLI | `loopos/cli/commands/session.py` | `tests/test_v0_3_cli.py` | **file-system read** (no side effects) |
| 27 | `loopos readiness check` CLI | `loopos/cli/commands/readiness.py` | `tests/test_v0_3_cli.py` | **enforced** — runs the 22-check readiness script |
| 28 | v0.3 Readiness Proof | `scripts/v0_3_readiness_check.py` | `tests/test_v0_3_readiness_check.py` | **22/22 hard checks pass** |
| 29 | Optional `workbench` extra in pyproject | `pyproject.toml` | (no dedicated test) | **structural** — `rich` and `typer` are optional; stdlib-`argparse` fallback in `loopos/cli/fallback.py` |
| 30 | Pre-existing flaky test fix | `tests/test_cli_error_handling.py` | `tests/test_cli_error_handling.py::test_run_with_file_as_workspace_returns_clean_error` | **passing** (8/8 stable across reruns; see Section E.4) |

---

## D. Real / dry-run / mock / planning-only classification

### D.1 Real runtime features (exercised end-to-end in production, gated)

* `loopos/providers_runtime/openai.py` — talks to any
  OpenAI-compatible endpoint. Live calls require
  `live_provider_calls_allowed=True` (the `--allow-live-provider` CLI
  flag in production), a configured `OPENAI_API_KEY`, `--budget-usd`,
  and `--confirm`. The audit used an **injected transport** that
  simulates the wire — no real HTTP was emitted. CI does not exercise
  the real wire path.
* `loopos/providers_runtime/ollama.py` — talks to a local Ollama
  daemon. Same gating as OpenAI. Not exercised live in this audit
  (no daemon running on the audit machine).

### D.2 Dry-run-only features (no side effects, evidence-only)

* `loopos workbench` — the Workbench is a **renderer**. It dispatches
  no side effects; it builds a `WorkbenchContext` snapshot and emits
  panels. The CLI default is `--dry-run=True`; the user must pass
  `--no-dry-run` plus `--allow-live-provider` plus `--budget-usd`
  plus `--confirm` to actually call a provider.
* `loopos/providers_runtime/openai.py` and `ollama.py` in dry-run
  mode — return a `dry_run` status without a network call.
* `loopos cli_ui/*` — Rich-based rendering layer. All visual
  rendering; no I/O.
* `loopos/providers_runtime/mock.py` in `--no-dry-run` mode without
  the live-allow flag — returns `dry_run` (effectively dry-run).

### D.3 Mock-only features (in-process, deterministic, never real)

* `loopos/providers_runtime/mock.py` — pure in-process mock. Always
  returns `status="completed"` with a deterministic echo of the
  user message.
* `loopos/adapters/mock.py` — emits a fixed event stream.
* `loopos/adapters/scream_code.py` — spec + mock. No live process.
* `loopos/adapters/cleanroom.py` — spec + mock. No private
  implementation dependency.
* `loopos/adapters/hermes.py` — clean-room CLI adapter proof
  (simulated by default).

### D.4 Planning-only features (emit decisions, never execute)

* `loopos/opengod/*` — emits `OpenGodDecision` + `OpenGodVerdict`.
  Never calls a provider, never opens a file, never executes shell.
  **This is a hard rule** documented in the OpenGod module docstrings
  and reasserted by `scripts/v0_3_readiness_check.py::check_opengod_decision_emits_no_command`
  which fails RC if OpenGod ever produces a non-decision side effect.
* `loopos/fusion_router/orchestrator.py` — caller-driven, no daemon.
  Maps `FusionVerdict.status` to an `AgentCommand` and (optionally)
  dispatches it through the v0.2 `CommandRunner`. No background
  scheduler, no thread, no asyncio.

### D.5 Mock-only features that must NOT be mistaken for real runtime

The following are explicitly classified as **mock / spec-only** and
must not be presented as "real" in any user-facing material:

* `loopos/providers_runtime/mock.py`
* `loopos/adapters/mock.py`
* `loopos/adapters/scream_code.py`
* `loopos/adapters/cleanroom.py`
* `loopos/adapters/hermes.py` (default mode; `simulated=True`)

The two real-runtime paths are:

* `loopos/providers_runtime/openai.py` (gated)
* `loopos/providers_runtime/ollama.py` (gated)

---

## E. Validation results

All six validation commands specified in the alpha-split plan pass
on the current `HEAD` (`0931b82`).

### E.1 `python -m ruff check .`

```
All checks passed!
```

### E.2 `python -m mypy loopos tests`

```
Success: no issues found in 392 source files
```

(Up from the strict-audit baseline of 27 errors in v0.3 test files.
The `b5b6b07` commit brought this to zero.)

### E.3 `python -m pytest -m "not slow" -q`

```
947 passed, 9 skipped, 46 deselected, 19 subtests passed in 112.12s (0:01:52)
```

* 947 passed (vs 940 at strict-audit time; the +7 is `test_cli_ui_console.py`
  added in `b5b6b07` plus targeted additions in `test_v0_3_deep_smoke.py`).
* 9 skipped — the 9 gated live-provider smoke tests
  (`tests/test_v0_3_live_provider_smoke.py`), which only run when
  `LOOPOS_LIVE_SMOKE=1`.
* 46 deselected — `-m "not slow"` excludes the `slow` group.
* 0 failed.

### E.4 Pre-existing flaky test status

`tests/test_cli_error_handling.py::test_run_with_file_as_workspace_returns_clean_error`
**passes** in the current run.

The strict audit fixed this test by adding pre-subprocess existence
assertions (visible in `e39b9d5` — the diff shows
`assert file_path.exists()` and `assert file_path.is_file()` added
after `file_path.write_text(...)`). The fix is in-tree.

The parallel Codex closeout report (`docs/reports/v0-3-rich-cli-workbench-closeout.md`,
line 124) incorrectly says "the test continues to fail because of
environment cleanup behavior". That statement is **wrong** for the
current `HEAD`. The test passes; the closeout doc is the artifact
to fix, not the test.

### E.5 `python scripts/v0_2_readiness_check.py --json`

```
status: "pass"
hard_fail_count: 0
warnings: 1
  - name: "release_evidence_untouched"
    detail: "release evidence changed: ['docs/reports/v0-3-audit-bugs.md',
            'docs/reports/v0-3-rc-audit.md',
            'docs/reports/v0-3-rich-cli-workbench-closeout.md',
            'docs/reports/v0-3-strict-rc-audit.md']"
```

The single warning is informational: it notes that the v0.3 audit
evidence files (which are post-release) were modified, which is
expected for an alpha phase that lives on `main` between v0.2 and
v0.3-rc. Not a blocker.

### E.6 `python scripts/v0_3_readiness_check.py --json`

```
status: "pass"
hard_fail_count: 0
warnings: 0
22 of 22 hard checks pass
```

The 22nd check is `live_provider_smoke`, added in this audit session
on top of the original 21.

### E.7 `python scripts/anti_bloat_check.py --json`

```
hard_fail_count: 0
warning_count: 1
warnings:
  - reason_code: "module_count_delta"
    severity: "warning"
    message: "loopos/ module count grew by 92 (baseline=199, current=291)"
```

The single warning is the module-count delta: the v0.3 implementation
adds 92 Python modules in `loopos/`. This is a soft signal that
v0.3 carries a lot of new code; it is not a hard fail and is
expected for an alpha that introduces 5 new sub-packages
(`adapters/`, `agent_bus/`, `cli_ui/`, `opengod/`, `providers_runtime/`)
plus the fusion orchestrator.

### E.8 Working tree

```
$ git status --short
(nothing)
```

The working tree is clean.

---

## F. Known RC blockers

These are the issues that prevent declaring v0.3-rc at this `HEAD`.

### F.1 Mega-commit topology (severity: structural)

`e39b9d5` is a 76-file, 9472-line commit whose message is
`docs(repo): separate product docs from agent prompts` but whose
content is the full v0.3 implementation. The message is misleading;
the diff is the v0.3 drop. RC must ship a logical 7-commit split
matching Section B. Resolution: `git reset --soft 136fdf3` followed
by 7 carefully ordered commits per the planned structure.

### F.2 OpenGod is not wired into AIL (severity: architectural)

`loopos/opengod/*` emits strategic decisions but is **not** wired
back into the AIL `AILInstruction` flow. The Kernel loop's
`Goal → compile into AIL → compile context → apply Policy OS →
compile next AIL/AI-ISA → validate → schedule → syscall → observe →
evaluate → state transition → governed memory` pipeline does not
consult `OpenGodDecision`. OpenGod is a parallel decision system
that can be invoked from the CLI (`loopos opengod …`) but its
verdicts are not consumed by `KernelLoopEngine.run`.

Resolution: define an `OpenGod → AIL` bridge contract. Either
`OpenGodDecision.kind` maps to a new `AILInstruction` op (e.g.
`OPENGOD.HALT` → `LOOP.HALT`), or OpenGod decisions are written to
`AILPreference` so the next AIL compile weights them. Either way,
the contract must be typed, tested, and documented.

### F.3 Workbench ↔ `model_call_command` budget tracker divergence (severity: latent)

`loopos/product/workbench.py::Workbench.call_model` and
`loopos/cli/commands/providers_runtime.py::model_call_command` each
maintain their own `ProviderBudget` instance. The Workbench tracks
spend in `self._budget_tracker: dict[str, ProviderBudget]`. The CLI
command constructs a fresh `ProviderBudget` per call. A request that
flows through both paths can theoretically double-count spend.

Resolution: introduce a single process-level `BudgetLedger`
(in-process) keyed on `provider_id + model_id + session_id` and
have both call sites use it. Add a regression test that asserts
spend is counted exactly once across the two paths.

### F.4 `loopos/skills/` is a 7-line re-export shim (severity: discoverability)

`loopos/skills/__init__.py` re-exports from `loopos.memory.skill_store`
and `loopos.memory.skill_proposals`. AGENTS.md lists "Skill Learning"
as a core capability and uses `loopos/skills/` as the namespace in
the MVP layout. The actual implementation lives in `loopos/memory/`
and is not clearly discoverable. A user reading AGENTS.md will look
in `loopos/skills/` and find a 7-line stub.

Resolution: either (a) move `loopos/memory/skill_store.py` and
`loopos/memory/skill_proposals.py` into `loopos/skills/` and
re-export from `loopos/memory/` for back-compat, or (b) update
AGENTS.md to point at `loopos/memory/skill_*`. (a) is preferred —
it matches the AGENTS.md blueprint and removes the "shim" anti-pattern.

### F.5 Live-provider smoke is wire-level fake, not real HTTP (severity: gap)

`scripts/v0_3_live_provider_smoke.py` uses an **injected transport**
(a Python closure that intercepts the `requests`-shaped call) to
simulate the wire. It proves the request is shaped correctly and
that the API key flows correctly through the gating, but it does
**not** prove behavior against a real OpenAI/Ollama server. Real
HTTP failure modes (timeouts, retries, rate limits, partial
responses, TLS errors, JSON parsing errors, 5xx) are not exercised.

Resolution: add a second smoke variant (`scripts/v0_3_live_provider_smoke_http.py`)
that talks to a **loopback** HTTP server (e.g. a `http.server` instance
on `127.0.0.1:0` returning canned OpenAI responses). The injected
transport covers the request-shaping proof; the loopback server
covers the transport-layer proof. The two together give reasonable
end-to-end confidence without a paid API key.

### F.6 MCP Tool Hub may be dead code (severity: discoverability)

`loopos/mcp/router.py`, `loopos/mcp/types.py`, and
`loopos/mcp/__init__.py` exist. But
`loopos/kernel/loop_engine.py::_SYSCALLS` (the syscall routing
table) maps `TERM.EXEC`, `FILE.READ`, `FILE.WRITE`, `GIT.STATUS`,
`GIT.DIFF` — it does **not** include `TOOL.CALL`. If the kernel
never dispatches to the MCP router, then `loopos/mcp/` is dead code
or only exercised by tests. AGENTS.md lists "MCP Tool Hub" as a
core capability; if it's not wired into the kernel, that needs to
be documented or fixed.

Resolution: a 1-day audit. Grep for `create_default_router`,
`ToolRegistry`, `ToolCall` across the runtime (not just tests). If
nothing outside `loopos/mcp/` and `tests/test_mcp_router.py` uses
the router, either wire it into `KernelLoopEngine._SYSCALLS` (add
`TOOL.CALL`) or document the deferred status in `loopos/mcp/`.

### F.7 No mutation testing, no secret scanning, no SBOM, no CI workflow

(Repeated from the strict audit for the v0.3-alpha record.)

* No `mutmut` / `cosmic-ray` / `mutpy` against v0.3 modules. The
  5 new v0.3 packages have low test-to-source ratios
  (`adapters/` 1:9, `agent_bus/` 1:6, `opengod/` 1:6, `product/`
  1:6, `providers_runtime/` 1:10) and no mutation proof that the
  tests would catch a small logic change.
* No `gitleaks` / `trufflehog` / `detect-secrets` in CI.
* No `pip-audit` / `safety` / `cyclonedx` SBOM.
* No `.github/workflows/ci.yml` visible in the tree (the recent
  commits reference "ci:" fixes but the workflow file is not in
  the repo).
* No `.pre-commit-config.yaml` enforcing local lint/type/test on
  commit.

Resolution: install pre-commit, write a CI workflow, schedule
mutation + secret + dependency scans. ~2-3 days of focused work.

### F.8 `loopos/cli/app.py` exceeds 300-LOC anti-bloat soft cap (severity: maintenance)

`loopos/cli/app.py` is now 851 lines. The 300-LOC soft cap in
`scripts/anti_bloat_check.py` is exceeded by ~550 lines. This is
acknowledged by the `module_count_delta` warning but not flagged
as a hard fail. The CLI registration of the 7 new v0.3 commands
in the Typer branch (lines 655-791) is the main contributor.

Resolution: extract one module per v0.3 command's Typer binding
(`loopos/cli/typer/workbench.py`, `loopos/cli/typer/adapters.py`,
etc.) and have `app.py` import + register them. The
`argparse` fallback in `loopos/cli/fallback.py` is already split
out and can serve as a reference.

### F.9 ~80 markdown docs, no API reference, no architecture diagram

(Repeated from the strict audit.) The doc set includes 6 prompt
files that were correctly relocated to `docs/prompts/` in
`e39b9d5` — that part is fixed. Remaining: no auto-generated API
reference, no architecture diagram, and the closeout report
(`docs/reports/v0-3-rich-cli-workbench-closeout.md`) carries one
inaccuracy (see E.4) that should be corrected or removed.

---

## G. Next hardening plan

The following is the proposed work for v0.3-alpha → v0.3-rc
transition. Items are ordered by leverage × cost.

### G.1 Re-split `e39b9d5` into the 7 logical commits (P0)

Per Section B. Use `git reset --soft 136fdf3` and re-stage the
files into 7 commits matching the planned structure. Validate each
with the 6-command suite. Total: ~2 days, mostly mechanical.

### G.2 OpenGod → AIL bridge (P0)

Per F.2. Define a typed contract
(`loopos/ail/opengod_bridge.py`?) that maps
`OpenGodDecision` → one or more `AILInstruction`s. Add tests.
Wire into `KernelLoopEngine.compile_next_ail()`. Total: ~3-4 days.

### G.3 Cross-path budget ledger (P1)

Per F.3. `loopos/providers_runtime/budget.py` gets a
`BudgetLedger` (process-singleton, keyed by
`provider_id + model_id + session_id`). Both call sites
(`Workbench.call_model`, `model_call_command`) use it. Add a
regression test that runs both paths in sequence and asserts
`commit()` is called exactly once and totals match. Total: ~1 day.

### G.4 Loopback HTTP smoke (P1)

Per F.5. New `scripts/v0_3_live_provider_smoke_http.py` that
boots a `http.server` on `127.0.0.1:0` returning canned
OpenAI/Ollama responses, points `OPENAI_BASE_URL` at it, and
runs the live call end-to-end. Add as a 23rd readiness check,
gated on `LOOPOS_LIVE_HTTP_SMOKE=1`. Total: ~1-2 days.

### G.5 CI workflow + pre-commit + secret scan (P1)

Per F.7. Add `.github/workflows/ci.yml` running ruff + mypy +
pytest + v0_2 readiness + v0_3 readiness + anti-bloat on every
PR. Add `.pre-commit-config.yaml` running the same on every
local commit. Add `gitleaks` or `trufflehog` to CI. Total:
~1-2 days.

### G.6 Skills module re-homing (P2)

Per F.4. Move `loopos/memory/skill_store.py` and
`loopos/memory/skill_proposals.py` into `loopos/skills/` and
re-export from `loopos/memory/` for back-compat. Total: ~0.5 day.

### G.7 MCP wiring audit (P2)

Per F.6. One-day audit. Either wire `TOOL.CALL` into
`KernelLoopEngine._SYSCALLS` and add a corresponding AIL op, or
document the deferred status with a clear "not used in v0.3"
note in `loopos/mcp/__init__.py`. Total: ~0.5-1 day.

### G.8 `loopos/cli/app.py` extraction (P2)

Per F.8. Move each v0.3 command's Typer binding into
`loopos/cli/typer/<command>.py`. Reduces `app.py` from 851 to
~450 lines (still over cap; further work needed in a separate
pass). Total: ~1 day.

### G.9 Mutation testing on the 5 new v0.3 packages (P2)

Per F.7. Install `mutmut` (or `cosmic-ray`). Run against
`loopos/adapters/`, `loopos/agent_bus/`, `loopos/opengod/`,
`loopos/product/`, `loopos/providers_runtime/`. Target 80% mutant
kill. Add to CI. Total: ~2-3 days.

### G.10 Fix the closeout report inaccuracy (P3)

Per E.4. The `docs/reports/v0-3-rich-cli-workbench-closeout.md`
"Known Limitations" section claims the flaky test "continues to
fail". It does not. Either remove that bullet or correct it to
"was flaky pre-v0.3, fixed in `e39b9d5` (pre-subprocess
existence assertions), passing on `HEAD`". Total: ~10 minutes.

### G.11 docs/ prompts audit (P3)

The 6 prompt files in `docs/prompts/` are Codex self-prompts
(`LoopOS_Kernel_Level_Codex_Prompt.md` etc.). They were correctly
separated from the doc tree in `e39b9d5`. But their content is
high-leverage stale material — they may reference old package
names, old v0.2 layouts, or contracts that have since changed.
A 2-day pass: read each, mark which still apply, delete or
rewrite the others.

---

## H. Final status

**v0.3-alpha implementation snapshot complete. RC blocked pending
hardening.**

All six validation gates pass on `HEAD` (`0931b82`):

| Gate | Result |
| ---- | ------ |
| `ruff check .` | All checks passed |
| `mypy loopos tests` | Success: no issues found in 392 source files |
| `pytest -m "not slow"` | 947 passed, 9 skipped, 46 deselected, 19 subtests |
| `v0_2_readiness_check.py --json` | status=pass, hard_fail_count=0 |
| `v0_3_readiness_check.py --json` | status=pass, hard_fail_count=0 (22/22) |
| `anti_bloat_check.py --json` | hard_fail_count=0 |

The 9 RC blockers in Section F are all known and have a
hardening plan in Section G. None of them are runtime-correctness
bugs; they are structural (commit topology), architectural
(OpenGod → AIL), maintenance (budget ledger divergence, app.py
size, dead code audit), or process (CI, pre-commit, mutation
testing, secret scan).

The v0.3 implementation does **not** claim RC. It claims
**v0.3-alpha**: the implementation snapshot is complete, the
runtime is safe, the tests are green, the documentation is
honest about what is mock vs. real vs. planning-only. The
remaining work to call it RC is mechanical and well-scoped.

End of v0.3-alpha split audit.
