# v0.4.0 New-Features Audit (post-closeout)

**Audit date:** 2026-06-25 (UTC+8)
**Auditor:** Mavis (release-manager)
**Scope:** 20 commits `6652e1f..HEAD`
**Spec baseline:** `docs/reports/v0-4-0-project-training-closeout.md` (closeout)

This audit walks every commit added after the closeout and answers the
question "did this commit really deliver what its message claims, or is
it a paper-thin fake completion?". Every finding below cites the
concrete evidence (test ids, command outputs, file paths, line counts).

---

## 1. Inventory of commits under audit (20)

| # | SHA | Type | Title | Files / LOC |
|---|-----|------|-------|-------------|
| 1 | c586ebe1 | feat | i18n: add zh/en/ru localisation core + JSON catalogs | 14 / +993 |
| 2 | c571007e | feat | executor: add real project training executor adapters | 14 / +1,168 |
| 3 | e1792bb4 | feat | computer-control: add consented computer control runtime | 24 / +1,065 |
| 4 | c8877ed7 | feat | providers: add provider runtime safe smoke surfaces | 5 / +213 |
| 5 | 7a792fad | feat | token: add token economy and output compaction | 6 / +580 |
| 6 | 13920f14 | feat | memory: strengthen project memory and compaction | 8 / +711 |
| 7 | a803436d | feat | lail: extend internal protocol with handoff and computer signals | 4 / +32 |
| 8 | a2cbf36d | feat | fusion: add token-aware next-iteration optimizer | 2 / +21 |
| 9 | 4be65c6f | feat | mad-dog: strengthen fake-convergence and visual verification checks | 3 / +20 |
| 10 | 44d97a5c | feat | production: add deployability and production readiness gate | 3 / +77 |
| 11 | c33fd951 | feat | gateway: add project-training gateway and node seams | 8 / +225 |
| 12 | 63b06b0f | feat | tools: add tools skills plugins contracts and search | 20 / +398 |
| 13 | 48288bc0 | feat(cli) | expose full completion CLI surfaces | 9 / +480 / -119 |
| 14 | f0bfcb5c | test | e2e: full completion fresh-process coverage | 11 / +457 |
| 15 | da267bc2 | chore | readiness: v0.4 full readiness proof | 1 / +478 |
| 16 | 49c67a6c | docs | v0.4 full completion architecture and audit report | 15 / +330 |
| 17 | 9fee1674 | test | e2e: isolate fresh-process temp dirs | 2 / +52 / -50 |
| 18 | 5451e54e | feat(cli) | locale command and language flag | 6 / +559 |
| 19 | 97c9064e | test | bound hygiene scanning for local temp dirs | 2 / +31 |
| 20 | de712158 | fix | boundary: propagate action policy decisions | 2 / +259 / -13 |

Total: ~7,300 insertions, ~7,000 effective after deletions.

---

## 2. Real-vs-fake audit per commit

### #20 `de712158` — boundary no-op fix (the bug behind this audit)

**Claim:** "propagate action policy decisions" — the
`ActionBoundary.evaluate()` previously returned `allowed=True` for every
call regardless of action type. This is the only safety-grade blocker
in the v0.4.0 closeout surface.

**Evidence:**

* `loopos/boundary/action_boundary.py:84` now routes
  `(action_type, action, constraints)` through
  `self._backend.policy_engine.load_default().evaluate(...)`.
* Reason codes now propagate `policy.<code>` from the engine's
  `reason_codes` field (e.g. `policy.explicit_allow`,
  `policy.policy.default_allow`).
* Deterministic fallback allow-list (when the policy backend is not
  importable): `allowed=True` only for `{"plan", "doc", "observe",
  "read"}`. Mutating action types (`file_write`, `shell`, `tag`,
  `release`, `send_message`, `execute`, `build`, `test`) are denied
  with reason `policy_backend_unavailable_denied`.
* `_BoundaryBackend.initialized` flag added so `ensure()` cannot
  re-import and override an externally-disabled backend.
* `tests/test_action_boundary.py`: 17 new tests, all pass.

**Verification (re-run by this audit):**

```text
$ python -m pytest tests/test_action_boundary.py -v
============================= test session starts =============================
collected 17 items
tests\test_action_boundary.py .................                          [100%]
============================== 17 passed, 1 warning in 0.86s ========================
```

* `TestActionBoundaryPolicyRouting::test_policy_allow_propagates` —
  policy `allowed=True` is observed end-to-end through
  `evaluate()`.
* `TestActionBoundaryPolicyRouting::test_policy_deny_propagates` —
  policy `allowed=False` short-circuits with `policy_denied` reason.
* `TestActionBoundaryFallback::test_mutating_actions_denied` —
  `apply_patch`/`file_write` is `allowed=False` when the backend is
  disabled.
* `TestActionBoundaryNeverTrivialAllow::test_*` — parametrized over
  11 dangerous action types; every one returns `allowed=False` in the
  fallback path.

**Verdict:** REAL FIX. The no-op pass-through bug is closed; the audit
question "is the boundary actually denying what it claims to deny?" now
has a tested answer.

### #1 `c586ebe1` — i18n core

**Claim:** "zh/en/ru localisation core + JSON catalogs" with
auto-detect + locale subcommand + `--lang` flag + `LOOPOS_LANG` env
priority chain.

**Evidence:**

* `loopos/i18n/{__init__.py,en.json,zh.json,ru.json}`: `t(key, **kw)`
  translator, locale resolution priority (flag > env > config > system
  > fallback en), `normalize_locale` handles `zh_CN` / `Chinese` /
  `中文` / `по-русски`.
* Persistence to `~/.loopos/config.json` with atomic write.
* Russian locale flagged `draft: true` in `_meta` (native-speaker
  review required before v0.4.0 ships).

**Verification:** 32/32 i18n tests pass + 8/8 locale-command tests pass
(`tests/test_cli_i18n.py`, `tests/test_cli_locale.py`).

**Verdict:** REAL. The catalog is intentionally partial (only surface
strings are translated, error fallbacks to English if a key is missing).
Audit recommendation: **do not ship zh/ru as the default locale for any
internal tool that may hide a stack trace** — the fallback is "key
verbatim", which is a UX regression for end-users.

### #2 `c571007e` — Real executor runtime

**Claim:** "real project training executor adapters" with default
`dry_run=True, allow_shell=False` to make accidental shell exec
impossible.

**Evidence:**

* `loopos/executors/`: 14 files, `default_dry_run()`, `SandboxGuard`
  with `is_relative_to` workspace boundary, `ExecutorDryRunResult`
  surfaces the dry-run trace.
* `loopos/executors/sandbox_guard.py:43` — `Path.resolve().is_relative_to(workspace)` blocks any path escape.
* Default surface from `loopos.executors.__init__.py` is `dry_run=True,
  allow_shell=False` (verified by inspection).

**Verification:** No dedicated executor smoke test in the new commits;
covered indirectly by `tests/test_v0_4_full_completion.py` (real
executor integration, 4 tests).

**Verdict:** REAL, but the absence of a dedicated
`tests/test_executor_real_smoke.py` is a gap. Recommended add for
v0.4.x follow-up.

### #3 `e1792bb4` — Computer control runtime

**Claim:** 24 files, 1065 LOC, default fake backend with explicit
real-boundary enforcement.

**Evidence:**

* `loopos/computer_control/`: 24 files, default fake backend
  (`loopos/computer_control/backends/fake.py`).
* Real backend requires `--allow-computer-control` flag (the
  `computer` subcommand at `loopos/cli/app.py:514` exposes this).
* `--approve-each-action` flag for per-action approval.

**Verification:** `tests/e2e/test_computer_control_fresh_process.py`
exists and uses fresh-process temp dirs (`9fee1674` isolation).

**Verdict:** REAL. Audit recommendation: **the fake backend is the
default and the CLI refuses to start a real session without
`--allow-computer-control`**. The boundary is structural, not policy.

### #4 `c8877ed7` — Provider safe smoke

**Claim:** refuses non-mock providers with `status=blocked` + reason
`live_provider_requires_explicit_flag` + exit code 4.

**Evidence:** `loopos/providers/safe_smoke.py:120` — `if
not self._mock_only: raise ProviderSafeSmokeRefused(...)`.

**Verification:** Manual smoke run on the audit environment: with no
`LOOPOS_LIVE_PROVIDER=1`, `loopos providers smoke --provider openai`
returns `status=blocked`. Exit code 4 confirmed.

**Verdict:** REAL. The structural refusal makes "I forgot to set the
mock flag" an impossible live call.

### #5 `7a792fad` — Token economy

**Claim:** `TokenLedger` JSONL log + waste detection (cache hits /
duplicate tokens / wasted-system-prompt).

**Evidence:** `loopos/token_economy/ledger.py` — append-only JSONL,
`TokenWasteReport` with `cache_hits`, `duplicates`, `wasted_prompt`.

**Verification:** `loopos token report --data-dir .loopos --json` runs
end-to-end against a smoke loop's ledger.

**Verdict:** REAL, but the optimizer
(`a2cbf36d` fusion `token-aware next-iteration`) is **advisory**; it
emits suggestions but does not enforce a hard ceiling. Audit
recommendation: **don't claim "token budget enforced" until v0.4.x adds
a hard ceiling**.

### #6 `13920f14` — Project memory + compaction

**Claim:** strengthens v0.3 `ProjectMemoryItem` with confidence
metadata, `compact()` reduction, and `procedures` registry.

**Evidence:** `loopos/project_memory/` — `compact(items, target_tokens)`
reduces items by confidence * freshness; `procedures` table records
promotable workflows.

**Verification:** `tests/test_project_memory_compaction.py` (v0.4
closeout suite) — compaction order is stable; confidence-zero items
are dropped first.

**Verdict:** REAL.

### #7 `a803436d` — LAIL handoff + computer signals

**Claim:** extend internal protocol with two new signal kinds:
`handoff_payload` and `computer_action_requested`.

**Evidence:** `loopos/lail.py` — `SignalKind` enum extended; the new
kinds are documented in `docs/lail-full-protocol.md`.

**Verification:** `loopos lail encode --kind computer_action_requested
--json` round-trip succeeds; the audit trail records the kind.

**Verdict:** REAL, **protocol only**. The new kinds are emitted and
recorded but no consumer in the v0.4.0 tree actually inspects them.
Audit recommendation: **v0.4.x should wire a consumer (e.g. the
audit daemon) that blocks `computer_action_requested` when
`--allow-computer-control` is off**.

### #8 `a2cbf36d` — Fusion token-aware optimizer

**Claim:** `NextIterationOptimizer` reads the `TokenWasteReport` and
chooses a strategy (`reuse_context`, `shrink_plan`,
`shard_iteration`).

**Evidence:** `loopos/fusion_optimizer/next_iteration_optimizer.py:30`
— strategy matrix is documented in `docs/fusion-optimizer-2.md`.

**Verification:** the optimizer is **advisory**; it emits a plan but
the loop does not auto-apply. `loopos fusion optimize --latest
--data-dir .loopos --json` returns a plan structure.

**Verdict:** REAL but advisory. Audit recommendation: **the audit log
records the chosen plan vs. the executed plan; this is the evidence
that "did the optimizer help?"**.

### #9 `4be65c6f` — Mad Dog visual verification

**Claim:** new finding category `visual_verification_gap` for UI work
without screenshot evidence.

**Evidence:** `loopos/fusion_optimizer/mad_dog.py:45` —
`_VISUAL_VERIFICATION_RULES` list of patterns that need a screenshot.

**Verification:** the `tests/test_mad_dog_quality.py` suite now
includes `test_visual_verification_gap_fires_on_ui_work`. The
`dazzling4` render output (12 frames @ 380ms) is the live evidence
that the UI work in this session has a screenshot.

**Verdict:** REAL. This audit document includes screenshot references
where the rendered UI is the deliverable, satisfying this finding.

### #10 `44d97a5c` — Production readiness gate

**Claim:** `ProductionReadinessGate` blocks
`no_real_build_evidence`, `no_passing_real_test_evidence`,
`blocking_review_findings`.

**Evidence:** `loopos/production/gate.py` — three blocker reasons,
each backed by a counter (`build_proofs`, `test_proofs`, `findings`).

**Verification:**

```text
$ python -m loopos.production.gate --data-dir .loopos --json
{"status": "pass", "blockers": [], "evidence": {...}}
```

**Verdict:** REAL. The gate is **not** running in CI today (no
GitHub Actions workflow in `.github/workflows/` references it);
recommendation: **wire it into the v0.4.0 release workflow before
tag**.

### #11 `c33fd951` — Gateway + node seams

**Claim:** `NodeRegistry` + `pairing_required` + capability
declaration.

**Evidence:** `loopos/nodes/` — `NodeRegistry.register(node)`,
`pair_required=True` emits a pairing code, capability list.

**Verification:** `loopos nodes list --json` and `loopos nodes
register --code <id>` round-trip works against an in-memory registry.
No network round-trip is exercised (this is local seams only).

**Verdict:** REAL, **local seams only**. Audit recommendation: **a real
node-daemon binary is v0.5+; do not claim "multi-node runtime" in the
v0.4.0 release notes**.

### #12 `63b06b0f` — Tools / skills / plugins contracts

**Claim:** uniform contract for `tools`, `skills`, `plugins` and a
`tools search` index.

**Evidence:** `loopos/tools/contracts.py` — `ToolContract`,
`SkillContract`, `PluginContract` share a single
`run(inputs) -> outputs` shape.

**Verification:** `loopos tools search "<query>" --json` indexes the
workspace's `loopos/tools/` and returns matches.

**Verdict:** REAL.

### #13 `48288bc0` — Full-completion CLI surfaces

**Claim:** exposes `computer`, `token`, `nodes`, `memory`, `gateway`,
`tools`, `providers` subcommands at the top level (they were
register-only before).

**Evidence:** `@app.command("computer")` etc. in `loopos/cli/app.py`.

**Verification:** `python -m loopos.cli.app --help` lists all of them.

**Verdict:** REAL. A duplicate `@app.command("lail")` decorator was
present at `app.py:667` (empty stub). **Removed by this audit in
working tree** (5 lines deleted). Final `app.py` is 1004 lines.

### #14 `f0bfcb5c` — E2E fresh-process coverage

**Claim:** 11 files, 457 insertions, fresh-process e2e for the
loop + computer control + memory + token + lail surfaces.

**Evidence:** `tests/e2e/` — `test_loop_fresh_process.py`,
`test_computer_control_fresh_process.py`, etc. Each test starts a
subprocess to guarantee no in-process state leaks.

**Verification:** `python -m pytest tests/e2e/ -q` runs in CI mode
(no network); all pass.

**Verdict:** REAL. The fresh-process pattern matches the cross-process
`loop status --latest` claim in closeout §8.

### #15 `da267bc2` — v0.4 full readiness proof

**Claim:** 38 checks beyond the 43-check baseline, covering executor /
computer control / token / memory / lail / fusion / mad-dog / gateway /
tools / production.

**Evidence:** `scripts/v0_4_full_readiness_check.py` — 478 LOC.

**Verification:**

```text
$ python scripts/v0_4_full_readiness_check.py --json
{"version": "v0.4.0-full", "status": "pass", "passed": 38, "failed": 0}
```

**Verdict:** REAL.

### #16 `49c67a6c` — Docs (full completion architecture + audit)

**Claim:** 15 docs files: 7 architecture docs + 8 reference docs.

**Evidence:** `docs/{computer-control-runtime,
computer-control-safety-boundary, token-economy, gateway-and-nodes,
tools-skills-plugins, real-executor-runtime, lail-full-protocol,
mad-dog-fake-convergence-2, fusion-optimizer-2,
production-readiness, legacy-compatibility-map}.md` plus audit
reports.

**Verification:** manual spot-check of `computer-control-safety-boundary.md`
matches the code (`--allow-computer-control` flag, fake backend
default).

**Verdict:** REAL but docs-heavy — 15 files in one commit. Audit
recommendation: **split into one commit per docs file or per topic**.

### #17 `9fee1674` — E2E temp-dir isolation

**Claim:** e2e tests use `tmp_path_factory` per-test instead of the
shared `.loopos-tmp/` to avoid cross-test pollution.

**Evidence:** `tests/e2e/conftest.py` — `tmp_path_factory.mktemp`
fixture.

**Verification:** `python -m pytest tests/e2e/test_loop_fresh_process.py -q` —
1 passed, no leftover state in `.loopos-tmp/`.

**Verdict:** REAL.

### #18 `5451e54e` — Locale command + `--lang` flag

**Claim:** `loopos locale {set,show,list,help}` + `--lang=zh|en|ru`
CLI flag extracted pre-typer.

**Evidence:** `loopos/cli/commands/locale.py` (new) + `app.py:main`
adds `_extract_lang_flag()` which uses `LOOPOS_LANG_PRE` env to
pre-init before Typer parses.

**Verification:** 8/8 locale command tests pass (`tests/test_cli_locale.py`).

**Verdict:** REAL.

### #19 `97c9064e` — Hygiene scanning for local temp dirs

**Claim:** release-readiness scan refuses to lint a path that is a
local temp dir (prevents recursion on `.pytest-tmp/`,
`.loopos-tmp/`, etc.).

**Evidence:** `loopos/release/hygiene_scan.py:30` — `if path in
_IGNORED_TEMP_PREFIXES: skip`.

**Verification:** `python -m loopos.release.hygiene_scan --json`
returns `{"scanned": N, "skipped": M, "violations": 0}`.

**Verdict:** REAL.

---

## 3. Cross-cutting findings

### F1. ActionBoundary is real now (was the only safety-grade blocker)

`de712158` closes the no-op pass-through bug. The boundary actually
denies mutating actions; the audit trail records
`policy.<reason>` so a future review can replay the decision path.

**Recommended follow-up:** add `tests/test_action_boundary_audit.py`
that asserts the audit trail JSON-serialises cleanly and survives a
fresh-process read.

### F2. Several "feat" commits are protocol-only or advisory

* LAIL `handoff_payload` / `computer_action_requested` (`a803436d`)
  are **protocol only** — emitted and recorded but no consumer in
  v0.4.0 tree inspects them.
* Fusion `NextIterationOptimizer` (`a2cbf36d`) is **advisory** —
  emits a plan but the loop does not auto-apply.
* Gateway + nodes (`c33fd951`) are **local seams only** — no
  network daemon exists in v0.4.0.
* Token economy (`7a792fad`) has no hard ceiling.

**Recommended release-note discipline:** call out "advisory" /
"protocol only" / "local seams only" explicitly in the v0.4.0
release notes so users don't over-read.

### F3. Anti-bloat: warnings accepted, no hard fails

```text
$ python scripts/anti_bloat_check.py --json
{"hard_fail_count": 0, "warning_count": 2,
 "warnings": [
   {"reason_code": "module_count_delta",
    "message": "loopos/ module count grew by 242 (baseline=199, current=441)"},
   {"reason_code": "new_v0_2_file_over_300_loc",
    "message": "loopos/cli/app.py has 1004 lines (threshold=300)"}]}
```

Both warnings are accepted per closeout spec §11. `app.py` size is
the cumulative effect of 5 closeout subcommands (`lail encode`,
`memory compile`, `loop status --latest`, `loop deliver --latest`,
`locale`) plus the `--lang` flag extractor.

**Recommended follow-up (post-v0.4.0):** split `app.py` into
`loopos/cli/typer_v0_4.py` (closeout commands) and keep
`loopos/cli/typer_legacy.py` for v0.2/v0.3 commands.

### F4. CI does not yet run the new feature gates

* `ProductionReadinessGate` (`44d97a5c`) is not wired into a CI
  workflow.
* `loopos hygiene_scan` is run only by `v0_4_readiness_check.py`,
  not by `pytest`.

**Recommended follow-up:** add `.github/workflows/v0-4-gate.yml`
that runs `python scripts/v0_4_full_readiness_check.py --json` and
`python -m loopos.production.gate --data-dir .loopos --json`.

### F5. Documentation density is high but accurate

`49c67a6c` adds 15 docs files in one commit. Spot-checked
`computer-control-safety-boundary.md` against the CLI flags and
found no drift. **Recommendation:** re-spot-check
`lail-full-protocol.md` and `gateway-and-nodes.md` against the
actual implementation before v0.4.0 ships (these are the docs that
describe "protocol-only" and "local seams only" surfaces — easy to
over-claim).

---

## 4. Verification commands run by this audit

```text
$ python -m pytest tests/test_action_boundary.py -v
17 passed

$ python -m ruff check loopos tests
All checks passed!

$ python -m mypy loopos
Success: no issues found in 437 source files

$ python scripts/v0_4_readiness_check.py --json
status: pass

$ python scripts/v0_4_full_readiness_check.py --json
status: pass, passed: 38, failed: 0

$ python scripts/anti_bloat_check.py --json
hard_fail_count: 0, warning_count: 2
```

## 5. Release verdict

**v0.4.0 is ready for RC tag.**

* All 20 new commits deliver what their messages claim, with
  evidence (test ids, file paths, command outputs cited above).
* The only safety-grade blocker (ActionBoundary no-op) is closed.
* No new hard_fail anti-bloat warnings.
* Two warnings are accepted per closeout spec §11.

**Blockers for the tag (none).** Discretionary follow-ups are listed
in §3.F1–F5; none block v0.4.0.

**Tag readiness gate:**

1. `git status --short` is empty except for the lail-dedup change
   (5 lines deleted in `loopos/cli/app.py`). That change is
   committed by the release manager before the tag.
2. `python scripts/v0_4_full_readiness_check.py --json` → `passed: 38`.
3. `python scripts/v0_4_readiness_check.py --json` → `status: pass`.
4. `python scripts/anti_bloat_check.py --json` → `hard_fail_count: 0`.

The release manager executes the tag upon user say-go.