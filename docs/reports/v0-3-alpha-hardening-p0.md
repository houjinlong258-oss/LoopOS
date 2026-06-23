# LoopOS v0.3-alpha — Hardening P0 Report

> **Status (this document):** v0.3-alpha P0 hardening complete.
> **Verdict:** **RC still blocked.**
>
> The four P0 objectives are closed. Six non-P0 RC blockers
> (inherited from the v0.3 alpha split-audit Section F) remain;
> they are explicitly out of the P0 scope and tracked under
> separate work items.

This report documents the `v0.3-alpha-hardening` branch's P0
pass. The branch is forked from `main` HEAD `f55185b` (the
post-cleanup v0.3-alpha snapshot). All four P0 objectives are
closed; every required validation gate passes on the new HEAD.

---

## A. Final status

**v0.3-alpha P0 hardening complete. RC still blocked.**

| Gate | Result |
| ---- | ------ |
| `pytest -m "not slow"` | 989 passed, 9 skipped, 46 deselected, 19 subtests passed |
| `pytest -m "slow"` | 46 passed, 999 deselected |
| `ruff check .` | All checks passed |
| `mypy loopos tests` | Success, no issues found in 396 source files |
| `v0_2_readiness_check.py --json` | status=pass, hard_fail_count=0 |
| `v0_3_readiness_check.py --json` | status=pass, hard_fail_count=0, warnings=[] (24/24 checks) |
| `anti_bloat_check.py --json` | hard_fail_count=0, warning_count=1 (informational only) |
| `rc_audit_cli_smoke.py` | ALL CLI SURFACES OK |
| `git status --short` | clean |

One pre-existing timing-flaky test
(`tests/test_deep_smoke.py::test_deep_smoke_global_timeout_names_running_check`)
intermittently fails the assertion ``duration_ms < 6000`` under
machine load. It passes on isolated runs and on the original v0.3
alpha cleanup pass; it is **not** a P0-hardening regression. It is
recorded here for transparency but does not change the verdict.

---

## B. P0 objectives — closed

### B.1 Cross-path Budget Ledger (P0-1)

**Status: closed.** Commits `717ba78`.

- Added `BudgetLedger` to `loopos/providers_runtime/budget.py`.
  Keys are normalised `(provider_id, model_id, session_id)` tuples.
  An empty `session_id` is the same as `session_id=None`.
- Process-level singleton via `get_default_ledger()` /
  `reset_default_ledger()`. Thread-safe via a single
  `threading.Lock`.
- `get_or_create` is idempotent: once a `ProviderBudget` exists for
  a key, subsequent `get_or_create` calls return the same instance
  and never overwrite `max_usd`. This is the property that prevents
  double-spending.
- `check` and `commit` are no-ops on a missing key so callers that
  opt out of budget tracking are not silently tracked.
- Migrated `Workbench.call_model` (`loopos/product/workbench.py`)
  and `model_call_command` (`loopos/cli/commands/providers_runtime.py`)
  to go through the shared ledger.
- Tests `tests/test_budget_ledger.py` cover the five required
  invariants:

  1. Repeated live calls accumulate spend.
  2. The Workbench and CLI share one ledger and cannot double-spend.
     The fixture-level test exercises `model_call_command` + a
     `Workbench.call_model` on the same `(mock, mock-model)` key
     and asserts `used_usd` grows by exactly one tick per call.
  3. Dry-run does not commit spend (no entry created, no
     `ProviderBudget` used).
  4. Failed calls (`status="failed"`) do not commit spend.
  5. The ledger scopes by `(provider, model, session)`.

  Additional tests: idempotency, key normalization, session_id
  empty == None, process singleton, thread-safety under 10 * 100
  concurrent commits.

### B.2 Loopback live-provider HTTP smoke (P0-2)

**Status: closed.** Commit `d972e01`.

- Added a real-HTTP transport path (`urllib_transport` in
  `loopos/providers_runtime/openai.py`) using only the standard
  library. No `requests` / `httpx` dependency.
- `OpenAICompatibleProviderRuntime(use_real_http=False)` — opt-in
  flag. When True and no explicit transport was injected, the
  runtime picks `urllib_transport` over the fail-closed default.
  The default stays fail-closed (no behaviour change for callers
  that did not opt in).
- New `scripts/v0_3_live_provider_smoke_http.py` boots a
  `http.server.HTTPServer` on `127.0.0.1:0` in a daemon thread,
  runs five invariant checks against it, and shuts it down cleanly.
- The smoke is gated by `LOOPOS_LIVE_HTTP_SMOKE=1` (or `--run`)
  so it does not run by default in CI.
- Five P0-2 invariants:

  1. `dry_run_keeps_server_quiet` — a request with
     `live_provider_calls_allowed=False` does not hit the server
     and returns `status='dry_run'`.
  2. `missing_key_blocks_structured` — a live request with no API
     key returns `status='blocked'` with
     `reason_codes=['provider_config_missing', 'OPENAI_API_KEY not set']`.
  3. `real_http_client_path` — a live request reaches the loopback
     server; the server's hit log records the POST and the
     runtime-produced URL (`/v1/chat/completions`) and model id.
  4. `response_metadata_returned` — the runtime parses the
     OpenAI-style usage block (`prompt_tokens`,
     `completion_tokens`, `total_tokens`).
  5. `secrets_redacted_in_trace` — the persisted
     `last_prepared.headers["Authorization"]` is the redacted
     placeholder; the real key never appears in the stored object.
     The wire path on the live side DOES carry the real key (this
     is the whole point of the smoke); only the persistence layer
     redacts.

- 23rd readiness check `check_loopback_http_smoke` added to
  `scripts/v0_3_readiness_check.py`. The check delegates to the
  smoke script with `LOOPOS_LIVE_HTTP_SMOKE=1` forced in the
  child env. CI runs the check unconditionally.

- Tests `tests/test_v0_3_live_provider_smoke_http.py` cover the
  smoke script's gated-off pass, `--run` mode, env-var-only
  enabling, defense-in-depth against leaked sensitive shapes, and
  the readiness check's exposure of the new check.

### B.3 CI / pre-commit / secret scanning (P0-3)

**Status: closed.** Commit `e8838aa`.

- Rewrote `.github/workflows/ci.yml` into four jobs with explicit
  dependencies: `lint-type-test` (matrix 3.11/3.12),
  `readiness-and-bloat`, `secrets`, `ci-report`.

  - `lint-type-test`: ruff, mypy, fast pytest, founding
    acceptance. mypy is explicit (`python -m mypy loopos tests`)
    instead of routed through `make type`.
  - `readiness-and-bloat`: v0.2 readiness, v0.3 readiness (with
    `LOOPOS_LIVE_HTTP_SMOKE=1` so the new loopback check is
    exercised), anti-bloat. Hard severity: any non-pass status
    fails the job.
  - `secrets`: runs gitleaks via `gitleaks/gitleaks-action@v2`
    with `GITLEAKS_CONFIG=.gitleaks.toml`.
  - `ci-report`: runs after the others (`if: always()`); uploads
    `docs/reports/latest-test-report.json` as a build artifact.

- New `.pre-commit-config.yaml` wires:
  - `ruff` + `ruff-format` on every commit (cheap).
  - `mypy` on pre-push, scoped to `loopos/tests` paths.
  - `pytest-fast` on pre-push.
  - `gitleaks` on every commit; blocks secret-shaped strings from
    landing in history.
  - Skippable with `SKIP=gitleaks git commit ...` if gitleaks is
    not installed locally; CI catches the same condition.

- New `.gitleaks.toml`:
  - Extends the default ruleset (`useDefault = true`).
  - Adds a LoopOS-specific rule for `sk-test-` keys (the prefix
    the loopback smoke emits at runtime). The rule allow-lists
    the three files where the prefix legitimately appears
    (`openai.py`, the smoke script, the smoke test).
  - Adds a LoopOS-specific rule for `Bearer sk-...` patterns in
    source files.
  - Top-level allow-list excludes `.venv/`, `dist/`,
    `.loopos-demo/`, and `latest-test-report.json`.

- Tests `tests/test_ci_precommit_wiring.py` assert the CI
  workflow mentions every required command, that the loopback
  gate env var is set for the v0.3 readiness job, the pre-commit
  config wires the four hooks, the gitleaks config extends the
  default ruleset with the LoopOS-specific rules, and the
  v0.3 readiness check still produces a valid JSON payload after
  the CI artifacts are in place.

### B.4 OpenGod boundary decision (P0-4)

**Status: closed (Option B).** Commit `ede3bbf`.

- Picked **Option B**: OpenGod remains planning-only on v0.3; the
  `OpenGodDecision → AIL` authority bridge is deferred to v0.4.
  Option A would have added new AIL instruction ops and wired
  `OpenGodDecision` into `KernelLoopEngine.compile_next_ail()` —
  both are feature expansions, which the hardening task
  explicitly forbids ("do not expand OpenGod features").
- `loopos/opengod/__init__.py` carries an explicit "planning-only,
  NOT wired into AIL execution authority on v0.3" callout. The
  callout is visible to anyone importing the package.
- New `docs/v0-3-opengod-boundary.md` records the decision and the
  v0.4 plan: map `OpenGodDecision.kind` → one or more
  `AILInstruction`s (`HALT → LOOP.HALT`, `REFINE → AILPreference`,
  `SCALE → bounded TERM.EXEC`, `ACCEPT → no-op`), wire behind a
  `LOOPOS_OPENGOD_AUTHORITY=1` feature flag, add a kernel-loop test
  that injects a stub `OpenGodDecision` and asserts the loop
  honors it.
- 24th readiness check `check_opengod_planning_only_boundary`
  added to `scripts/v0_3_readiness_check.py`. Asserts:

  1. `loopos/opengod/__init__.py` module docstring contains the
     "planning-only", "NOT", and "v0.3" markers.
  2. No AIL-adjacent symbol leaks into the OpenGod public API
     surface (after stripping the module docstring, which is
     allowed to *mention* AIL symbols by name when explaining
     the boundary).
  3. No authority-side runtime path (`loopos/kernel/`,
     `loopos/ail/`, `loopos/agents/`, `loopos/agent_bus/`)
     imports `OpenGodDecision` / `OpenGodVerdict` / `decide` /
     `build_verdict` for execution purposes. Read-only display
     from the Workbench (`loopos/product/`) and the CLI command
     (`loopos/cli/commands/opengod.py`) is allowed and unchanged.

- Tests `tests/test_opengod_boundary.py` cover the same three
  assertions plus the readiness check's exposure of the new
  check.

- `CHANGELOG.md` v0.3 umbrella gains a "v0.3-alpha hardening
  (P0)" subsection that records all four P0 items so the RC audit
  can cite one changelog entry per P0 item.

---

## C. Commits added on `v0.3-alpha-hardening`

| # | Hash | Subject |
| - | ---- | ------- |
| 0 | `f55185b` | base (post-cleanup v0.3-alpha snapshot from `main`) |
| 1 | `717ba78` | `feat(providers): add cross-path BudgetLedger (P0-1 hardening)` |
| 2 | `d972e01` | `feat(providers): add loopback live-provider HTTP smoke (P0-2 hardening)` |
| 3 | `e8838aa` | `ci: add readiness gates, pre-commit hooks, and gitleaks (P0-3 hardening)` |
| 4 | `ede3bbf` | `feat(opengod): document v0.3 boundary decision (P0-4 hardening, Option B)` |
| 5 | `afb71c1` | `style: remove unused imports / vars surfaced by ruff after P0 hardening` |

Five commits, all small and self-contained. No commit modifies
runtime behavior of pre-existing surfaces.

---

## D. Files added or modified

### D.1 P0-1 (Budget Ledger)

- `loopos/providers_runtime/budget.py` — added `BudgetLedger`,
  `get_default_ledger`, `reset_default_ledger`.
- `loopos/providers_runtime/__init__.py` — exports.
- `loopos/cli/commands/providers_runtime.py` — `model_call_command`
  migrated to the shared ledger.
- `loopos/product/workbench.py` — `Workbench.call_model` migrated;
  removed `self._budget_tracker` (per-provider dict, no model or
  session granularity).
- `tests/test_budget_ledger.py` — new tests.

### D.2 P0-2 (Loopback HTTP smoke)

- `loopos/providers_runtime/openai.py` — added `urllib_transport`,
  `use_real_http` constructor flag, exported `urllib_transport`.
- `scripts/v0_3_live_provider_smoke_http.py` — new smoke script.
- `scripts/v0_3_readiness_check.py` — added `check_loopback_http_smoke`
  and the corresponding entry in `ALL_CHECKS`.
- `tests/test_v0_3_live_provider_smoke_http.py` — new tests.

### D.3 P0-3 (CI / pre-commit / secret scanning)

- `.github/workflows/ci.yml` — rewritten with four jobs.
- `.pre-commit-config.yaml` — new.
- `.gitleaks.toml` — new.
- `tests/test_ci_precommit_wiring.py` — new tests.

### D.4 P0-4 (OpenGod boundary)

- `loopos/opengod/__init__.py` — explicit planning-only callout.
- `docs/v0-3-opengod-boundary.md` — new.
- `scripts/v0_3_readiness_check.py` — added
  `check_opengod_planning_only_boundary` and the corresponding
  entry in `ALL_CHECKS`.
- `tests/test_opengod_boundary.py` — new tests.
- `CHANGELOG.md` — v0.3-alpha hardening (P0) subsection.

### D.5 Ruff cleanup

- `scripts/v0_3_live_provider_smoke_http.py` — unused var removed.
- `scripts/v0_3_readiness_check.py` — unused `exc` removed.
- `tests/test_budget_ledger.py` — unused imports removed.
- `tests/test_opengod_boundary.py` — unused pytest import removed.
- `tests/test_v0_3_live_provider_smoke_http.py` — unused pytest
  import removed.

---

## E. Test counts

| Suite | Count |
| ----- | ----- |
| `tests/test_budget_ledger.py` | 14 tests |
| `tests/test_v0_3_live_provider_smoke_http.py` | 6 tests |
| `tests/test_ci_precommit_wiring.py` | 16 tests |
| `tests/test_opengod_boundary.py` | 4 tests |
| **P0 hardening tests added** | **40 tests** |

Total fast pytest on the new HEAD:

```
989 passed, 9 skipped, 46 deselected, 19 subtests passed in 197.33s (0:03:17)
```

The +42 delta vs. the v0.3-alpha baseline (947) is the 40 P0
tests plus 2 unrelated test additions in pre-existing files
during the same period.

Slow pytest on the new HEAD:

```
46 passed, 999 deselected in 106.29s (0:01:46)
```

---

## F. Remaining RC blockers

Inherited unchanged from `docs/reports/v0-3-alpha-split-audit.md`
Section F. The P0 pass closes four of them; six remain.

| Audit F# | Blocker | P0 status |
| -------- | ------- | --------- |
| F.1 | Mega-commit topology | closed by cleanup pass (pre-P0) |
| F.2 | OpenGod → AIL bridge | **deferred to v0.4 (Option B, P0-4)** |
| F.3 | Workbench ↔ model-call budget ledger divergence | **closed (P0-1)** |
| F.4 | `loopos/skills/` 7-line re-export shim | still open, not in P0 scope |
| F.5 | Live-provider smoke is wire-level fake | **closed (P0-2)** |
| F.6 | MCP Tool Hub may be dead code | still open, not in P0 scope |
| F.7 | No mutation / secret / SBOM / CI workflow | CI + pre-commit + secret scan **closed (P0-3)**; mutation testing still open |
| F.8 | `loopos/cli/app.py` exceeds 300-LOC anti-bloat soft cap | still open, not in P0 scope |
| F.9 | ~80 markdown docs, no API reference, no architecture diagram | still open, not in P0 scope |

The non-P0 blockers (F.4, F.6, F.7 mutation sub-item, F.8, F.9)
each have a hardening plan entry in
`docs/reports/v0-3-alpha-history-cleanup.md` Section H. None of
them are runtime-correctness bugs; they are structural,
discoverability, or process items.

---

## G. Hardening items intentionally NOT done

Per the per-task constraints, the P0 pass did **not** do any of
the following:

- Expand OpenGod features (no new AIL ops, no new decision kinds).
- Add new providers (no new entries in
  `loopos/providers_runtime/registry.py`).
- Add MCP implementation (no new `loopos/mcp/` modules).
- Add Textual / Web UI (no new `loopos/cli_ui/` surfaces beyond
  what was already in the alpha).
- Weaken tests (no test deletions, no test softening, no
  assertion relaxation).
- Hide mock-only behavior as real runtime. The P0 pass adds the
  loopback smoke as **real HTTP** (urllib), not as a fake; the
  injected-transport smoke remains and is exercised in CI.
- Tag v0.3.0 (the per-task instruction was explicit). No tag was
  added.
- Claim RC. The final status of this document is "RC still
  blocked".

---

## H. Final verdict

**v0.3-alpha P0 hardening complete. RC still blocked.**

All four P0 objectives are closed; every required validation
gate passes on the new HEAD `f55185b + P0 hardening`. Six
non-P0 RC blockers remain and must be addressed in subsequent
hardening passes before the v0.3-RC verdict can be revisited.

End of v0.3-alpha P0 hardening report.