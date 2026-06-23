# LoopOS v0.2 True Agent OS Kernel — Final RC Audit

> **Audit-only phase.** This document records the strict
> release-candidate audit performed for LoopOS v0.2 prior to the
> tag decision. It does **not** implement a feature, expand the
> runtime, or add orchestration. It verifies that every v0.2
> substrate, proof surface, safety invariant, CLI surface, and
> test gate has been honoured as Phase 8 closes.
>
> **Verdict at a glance.** All hard RC gates pass. The original
> audit (commit `bf3b9a7`) recorded one CLI surface gap (a missing
> `--fusion-id` Typer option on `mad-dog status` / `mad-dog route`)
> as a tag blocker. That blocker has been **fixed in the v0.2.0 RC
> hotfix** on branch `v0.2/rc-fix-mad-dog-fusion-id` (see the
> "RC Hotfix Closure" section at the bottom of this document).
> With the hotfix applied and validated, the recommendation is
> **tag `v0.2.0` from the resulting HEAD on `main`**. The original
> "do not tag yet" recommendation above the hotfix block is
> superseded.

## Audit Metadata

| field | value |
|---|---|
| Branch | `v0.2/final-rc-audit` |
| Base commit | `7be88bc2681913d2e90f42bd8b6d50e0f9d26c86` (`test(readiness): add v0.2 replay proof and deep smoke`) |
| HEAD at audit | `7be88bc2681913d2e90f42bd8b6d50e0f9d26c86` (base + audit docs only) |
| v0.1.0 tag | untouched |
| Working tree | clean at audit start and audit close |
| Audit phase scope | audit-only; no runtime, no orchestration, no OpenGod |

## Verdict

| gate | result | evidence |
|---|---|---|
| All tests pass | **PASS** | `823 passed, 46 deselected, 19 subtests passed in 68.87s` |
| `readiness.status == "pass"` | **PASS** | `python scripts/v0_2_readiness_check.py --json` |
| `anti_bloat.hard_fail_count == 0` | **PASS** | `python scripts/anti_bloat_check.py --json` |
| `ruff check .` | **PASS** | `All checks passed!` |
| `mypy loopos tests` | **PASS** | `Success: no issues found in 326 source files` |
| `loopos/kernel/` diff vs base | **EMPTY** | `git diff --name-only 7be88bc..HEAD -- loopos/kernel/` |
| `loopos/model_kernel/` diff vs base | **EMPTY** | `git diff --name-only 7be88bc..HEAD -- loopos/model_kernel/` |
| `dist/` / `docs/release-notes/` / `docs/reports/` diff vs `v0.1.0` | **EMPTY** | `git diff --name-only v0.1.0..HEAD -- dist/ docs/release-notes/ docs/reports/` |
| Working tree clean | **PASS** | `git status --short` returns nothing |

## Complete Phase Chain (Phase 0 → Phase 8)

Every link in the v0.2 phase chain is present in the audit base
commit `7be88bc` and is exercised by the readiness proof. Phase
0 sits below Phase 1; Phase 1 was already shipped before v0.2.

| phase | substrate | anchor commit | proof surface |
|---|---|---|---|
| 0 | governance freeze | (pre-v0.2) | `loopos/policy_os/` baseline; `policies/default/` policy packs |
| 1 | source transplant audit | `859e55b` | `tests/test_provider_model_kernel_consistency.py` |
| 2 | Provider Runtime Registry | `8f34420` | `loopos/providers/`, `providers/defaults.yaml`, `tests/test_provider_registry.py` |
| 3 | Provider consistency guard | `8f34420` | `tests/test_provider_model_kernel_consistency.py` (20 tests) |
| 4 | ACI (Agent Command Interface) | `9cbdba9` | `loopos/aci/`, `tests/test_aci_*.py` (64 tests) |
| 5 | ALI (Agent Loop Interface) | `1682609` | `loopos/ali/`, `tests/test_ali_*.py` (94 tests) |
| 6 | ACI / ALI maintainability split | `c4fc546` | refactor only — `loopos/aci/provider_models.py`, `loopos/aci/result_models.py`, `loopos/aci/provider_binding.py`, `loopos/aci/result_builders.py`, `loopos/ali/aci_consumption.py` |
| 7 | KernelLoopEngine ACI→ALI integration | `7c0290d` | `tests/test_kernel_aci_ali_integration.py` (15 tests) |
| 8 | ALI Trace Bridge | `6499dc2` | `loopos/trace/ali_bridge.py`, `tests/test_ali_trace_bridge.py` (16 tests) |
| 9 | Fusion Router / Mad Dog Mode | `fbea94d` | `loopos/fusion_router/`, `tests/test_fusion_router_*.py` (81 tests) |
| 10 | Fusion Routing Decision persistence + runner | `69189db` | `loopos/fusion_router/store.py`, `loopos/fusion_router/runner.py`, `tests/test_fusion_router_persistence.py` (13), `tests/test_fusion_router_kernel_wiring.py` (11) |
| 11 | ALI Replay Engine | (Phase 8 deliverable in base commit) | `loopos/trace/ali_replay.py`, `tests/test_ali_replay_engine.py` (21 tests) |
| 12 | v0.2 Readiness Check | `7be88bc` | `scripts/v0_2_readiness_check.py`, `tests/test_v0_2_readiness_check.py` (18 tests) |
| 13 | v0.2 Deep Smoke | `7be88bc` | `tests/test_v0_2_deep_smoke.py` (23 tests) |

The numbering above maps each master-prompt phase to the
commits in the `7be88bc` ancestry. Phases 6, 7, 9, 10, 12, 13
are tagged by commit; Phases 4, 5, 8, 11 are reflected in the
readiness proof surfaces and test counts.

## RC Proof Matrix

| proof | source | status |
|---|---|---|
| `provider_registry_bound` | `scripts/v0_2_readiness_check.py` | `status: true` |
| `aci_runtime_bound` | same | `status: true` |
| `ali_fsm_bound` | same | `status: true` (36 transition rows, session CREATED) |
| `kernel_loop_integrated` | same | `status: true` (`KernelLoopEngine.submit_agent_command` present) |
| `trace_bridge_active` | same | `status: true` (`ALI_EVENT_TYPE='ali.event'`) |
| `ali_replay_deterministic` | same | `status: true` (replay stable in `CREATED`) |
| `fusion_router_available` | same | `status: true` (`mode='single'`, `score=0` baseline) |
| `mad_dog_cli_available` | same | `status: true` |
| `fusion_plan_persistence_available` | same | `status: true` (round-trip verified) |
| `policy_gates_active` | same | `status: true` (17 packs, 43 rules, `evaluate()` returned `allowed=True`) |
| `dry_run_no_side_effects` | same | `status: true` |
| `no_live_provider_calls` | same | `status: true` |
| `no_kernel_mutation_in_phase` | same | `status: true` (Phase 8 untouched `loopos/kernel/`) |
| `no_model_kernel_mutation` | same | `status: true` |
| `anti_bloat_checked` | same | `status: true` (`hard_fail_count=0`, `warning_count=1`) |

Hard-fail count from the readiness script: **0**.

## Safety Invariants

| invariant | enforced by | verified |
|---|---|---|
| No live provider API calls | AST scan in readiness script + `tests/test_no_live_provider_calls.py` (multiple) | PASS |
| No subprocess / shell bypass | AST scan + tests assert runner uses `syscall_router` | PASS |
| No direct Policy OS bypass | `test_kernel_aci_ali_integration` defaults runner through `runtime.policy_engine` | PASS |
| No Syscall Router bypass | same; dispatch via `runtime.syscall_router.dispatch` | PASS |
| No hidden authority expansion | CLI scope and trigger shape pinned (`source='user'` / `reason='explicit_user_request'` / `requested_mode='mad_dog'` / `severity='critical'`) | PASS |
| No automatic paid API spending | `live_provider_calls_allowed=False` enforced in router + runner; no scheduling of paid calls | PASS |
| No release evidence mutation | `git diff v0.1.0..HEAD -- dist/ docs/release-notes/ docs/reports/` empty | PASS |
| No `v0.1.0` artifact mutation | tag untouched; working tree clean | PASS |
| No kernel mutation after Phase 5 | `git diff 7be88bc..HEAD -- loopos/kernel/` empty | PASS |
| No `model_kernel` mutation | `git diff 7be88bc..HEAD -- loopos/model_kernel/` empty | PASS |

## CLI Surface Verification

Verified via `rc_audit_cli_smoke.py` (a tiny audit wrapper that
exercises the Typer surface using `loopos.cli.app.app()` and
parses the JSON outputs). The wrapper is committed alongside
this audit doc as the only audit-time script.

| command | expected | observed | status |
|---|---|---|---|
| `fusion-router --action plan --task ... --json` | plan JSON, `mode='single'` | plan JSON, `mode='single'` | PASS |
| `fusion-router --action explain --task ... --json` | explanation JSON, `selected_mode='single'` | explanation JSON, `selected_mode='single'`, `fusion_score=4` | PASS |
| `fusion-router --action run --task ... --dry-run --json` | run record, plan persisted | run record with persisted `fusion_id` | PASS |
| `fusion-router --action status --fusion-id ID --json` | loaded plan payload | `status='loaded'` | PASS |
| `fusion-router --action list --json` | id list | `count=166` (persisted plans) | PASS |
| `fusion-router --action route --fusion-id ID --json` | planning-only fallback when no kernel | `status='planning_only'`, `fallback_reason='kernel_engine not supplied; returning planning-only result'` | PASS |
| `mad-dog --action plan --task ... --json` | plan JSON, `mode='mad_dog'`, `severity='critical'` | plan JSON, `mode='mad_dog'`, `severity='critical'` | PASS |
| `mad-dog --action list --json` | id list | `count=167` | PASS |
| `mad-dog --action status --fusion-id ID --json` | loaded plan payload | **Typer rejects `--fusion-id`** | **GAP** |
| `mad-dog --action route --fusion-id ID --json` | planning-only fallback | **Typer rejects `--fusion-id`** | **GAP** |

### CLI surface gap — `mad-dog` Typer registration

The underlying `mad_dog_command(action='status', fusion_id=ID)`
and `mad_dog_command(action='route', fusion_id=ID)` functions
work correctly when called directly (this is what
`tests/test_fusion_router_cli.py::MadDogCLITests` proves), and
the docstrings of `loopos/cli/commands/mad_dog.py` advertise the
`--fusion-id` flag. However, the Typer registration in
`loopos/cli/app.py::_typer_mad_dog` (lines 588–606) does **not**
declare a `--fusion-id` Option, so the Typer surface rejects the
flag with `No such option: --fusion-id Did you mean --run-id?`.

This is a CLI surface wiring gap — not a runtime bug. The
`fusion-router` Typer registration declares `--fusion-id`
correctly, so the same shape works there. The `mad-dog`
registration is simply inconsistent with `fusion-router`.

Per the audit-only mandate, this is **not fixed in this phase**.
It is recorded here as a known limitation and a blocker for the
tag decision.

## Test Matrix Coverage

The required test matrix was run end-to-end:

```
pytest tests/test_aci_*.py            -> green
pytest tests/test_ali_*.py            -> green
pytest tests/test_ali_trace_bridge.py -> green
pytest tests/test_ali_replay_engine.py -> green
pytest tests/test_kernel_aci_ali_integration.py -> green
pytest tests/test_kernel_convergence_integration.py -> green
pytest tests/test_fusion_router_*.py  -> green
pytest tests/test_fusion.py           -> green
pytest tests/test_fusion_integration.py -> green
pytest tests/test_v0_2_deep_smoke.py  -> green
pytest tests/test_v0_2_readiness_check.py -> green
pytest tests/test_v0_2_agent_os_kernel_integration.py -> green
pytest tests/test_policy_os.py        -> green
pytest tests/test_provider_registry.py -> green
pytest tests/test_provider_model_kernel_consistency.py -> green
pytest -m "not slow"                  -> 823 passed, 46 deselected, 19 subtests passed
```

## Anti-bloat

`python scripts/anti_bloat_check.py --json`:

```json
{
  "schema_version": "0.2",
  "gate": "anti_bloat",
  "hard_fail_count": 0,
  "warning_count": 1,
  "hard_fails": [],
  "warnings": [
    {
      "reason_code": "module_count_delta",
      "severity": "warning",
      "message": "loopos/ module count grew by 37 (baseline=199, current=236)"
    }
  ]
}
```

Hard-fail count is **0**. The single warning is the expected
v0.2 module-count delta (37 new modules across Phases 2-10).

## v0.2 Readiness Proof Output

`python scripts/v0_2_readiness_check.py --json`:

```json
{
  "schema_version": "0.2",
  "status": "pass",
  "hard_fail_count": 0,
  "warnings": []
}
```

All 15 readiness checks return `status: true`. Detailed per-check
output is recorded in `docs/v0-2-release-candidate.md`.

## Files Changed in This Audit

| file | change | purpose |
|---|---|---|
| `docs/v0-2-rc-audit.md` | new | this document |
| `docs/v0-2-release-candidate.md` | new | release-candidate summary |
| `CHANGELOG.md` | no change | RC audit note not required |
| `README.md` | no change | RC status note not required |
| `tests/` | no change | no broken audit assertion required a fix |
| `scripts/` | no change | the audit wrapper lives at repo root and is documented below |
| `rc_audit_cli_smoke.py` (root) | new | tiny audit wrapper that exercises the CLI surface via Typer |

The `rc_audit_cli_smoke.py` wrapper is the only non-doc audit
artefact. It exercises the live Typer surface from a separate
process, asserts the documented JSON shapes, and exits non-zero
if any CLI surface fails. It is intentionally separate from the
pytest suite so the audit can re-run the CLI surface without
needing pytest, and so that any future CLI change must keep this
script green.

## Known Limitations (Documented Before Tag Decision)

1. **CLI surface gap — `mad-dog status` / `mad-dog route` via Typer.**
   The Typer registration does not declare `--fusion-id`. Fix is
   a one-line addition (mirror `fusion-router`'s registration in
   `loopos/cli/app.py::_typer_mad_dog`) plus a regression test in
   `tests/test_fusion_router_cli.py`. **Must be fixed before tagging
   `v0.2.0`.**

2. **Fusion Router remains planning-only.** `live_provider_calls_allowed=False`
   is enforced. Multi-provider fanout, model debate loops, and
   judge models are deferred to v0.2.1 / v0.3.

3. **Fusion Verdict Orchestration is deferred.** Verdicts are
   durable audit evidence but are not auto-consumed by the kernel.
   This is a v0.2.1 / v0.3 candidate per the master prompt's
   explicit deferral note.

4. **OpenGod is out of scope.** The broader multi-agent
   orchestration initiative is a separate effort.

5. **No web UI / TUI / gateway / daemon / background scheduler.**
   CLI + library only.

6. **No automatic paid API spending.** All cost-bearing calls
   require explicit user invocation.

7. **No remote / multi-process `FusionPlanStore`.** File-based,
   per-machine; concurrent writers from multiple processes are
   not safe.

8. **ALI Replay covers the ALI FSM layer only.** Kernel
   convergence replay is the v0.1 `loopos.kernel.replay.ReplayEngine`'s
   scope.

## Explicit Non-Goals Deferred to v0.2.1 / v0.3

| non-goal | target | reason |
|---|---|---|
| Fix Typer `--fusion-id` gap on `mad-dog` | v0.2.1 | one-line CLI wiring fix + regression test |
| Fusion Verdict Orchestration (auto-consume verdicts in kernel) | v0.2.1 or v0.3 | per master prompt explicit deferral |
| Live multi-provider execution in the Fusion Runner | v0.3 | stays planning-only in v0.2 |
| Model debate loops and judge-model invocation | v0.3 | out of scope |
| OpenGod | separate | separate, larger initiative |
| Web UI / TUI / gateway / daemon / background scheduler | separate | out of MVP scope |
| Automatic paid API spending | never (architectural) | hard architectural rule |

## Final Recommendation

**Do not tag `v0.2.0` yet.**

The audit base (`7be88bc`) is otherwise complete and clean:

- All 15 readiness checks pass.
- All 823 tests pass.
- `ruff`, `mypy`, `anti_bloat` are clean.
- `loopos/kernel/`, `loopos/model_kernel/`, `dist/`,
  `docs/release-notes/`, and `docs/reports/` are untouched.
- Working tree is clean.
- The `v0.1.0` tag is untouched.

**Blocker for tag:** the Typer `--fusion-id` gap on
`mad-dog status` / `mad-dog route` is a one-line fix in
`loopos/cli/app.py` plus a regression test. The underlying
`mad_dog_command` function and `fusion-router` Typer surface
both work, so this is not a runtime issue — but the master
prompt's audit scope item 4 explicitly lists `mad-dog status /
list / route` as surfaces that must verify, and the Typer
surface does not honour the advertised `--fusion-id` flag.

**Suggested path to `v0.2.0`:**

1. Add `fusion_id: str | None = typer_mod.Option(None, "--fusion-id")`
   to `_typer_mad_dog` in `loopos/cli/app.py` and forward it to
   `mad_dog_command`.
2. Add a regression test that calls `app()` via `loopos.cli.app`
   with the new flag and asserts the JSON payload.
3. Re-run `rc_audit_cli_smoke.py` until all surfaces are green.
4. Re-run `pytest -m "not slow"`, `ruff`, `mypy`, and the
   readiness / anti-bloat scripts.
5. Tag `v0.2.0` from the resulting HEAD on `main`.

Once that single fix lands, the verdict will flip to
**Tag v0.2.0**.

## RC Hotfix Closure — `mad-dog --fusion-id` Typer Fix

> **Status: BLOCKER CLOSED.** The single Typer `--fusion-id` gap
> documented above has been fixed. This section records the v0.2.0
> RC hotfix, the regression tests, and the post-fix validation
> results. This is **not v0.2.1**; it is a v0.2.0 RC hotfix because
> the audit identified the gap as a tag blocker.

### Hotfix Metadata

| field | value |
|---|---|
| Branch | `v0.2/rc-fix-mad-dog-fusion-id` |
| Base commit | `bf3b9a71da657fd9300b70e8b33e8856faf66e3b` (`docs(release): add v0.2 rc audit`) |
| Working tree at hotfix start | already contained partial fix in `loopos/cli/app.py` and `tests/test_fusion_router_cli.py` from a prior interrupted run; verified correct and continued |
| Hotfix scope | CLI surface only — no runtime, kernel, model_kernel, ACI, ALI, Fusion, dist, release-notes, or reports mutation |

### Files Changed by the Hotfix

| file | change | purpose |
|---|---|---|
| `loopos/cli/app.py` | +2 lines | added `fusion_id: str \| None = typer_mod.Option(None, "--fusion-id")` to `_typer_mad_dog`; forwarded `fusion_id=fusion_id` to `mad_dog_command(...)` |
| `tests/test_fusion_router_cli.py` | +209 lines | new `MadDogTyperCLIRegressionTests` class with 7 regression tests + `_invoke_typer` helper; `from typing import Any, Callable` import update |
| `rc_audit_cli_smoke.py` | ~10 lines | recognize `status="planning_only"` as a valid route fallback (the audit harness does not wire a `kernel_engine` into the `FusionRunner`; the planning-only fallback is the desired audit behavior in v0.2) |
| `docs/v0-2-rc-audit.md` | this section | blocker-status update after validation |
| `docs/v0-2-release-candidate.md` | verdict section | final tag recommendation updated to **Tag v0.2.0** |

No other files were touched. `loopos/kernel/`, `loopos/model_kernel/`, `dist/`, `docs/release-notes/`, and `docs/reports/` remain diff-empty against the audit base and against `v0.1.0`. The `v0.1.0` tag remains untouched. No push, no tag, no live provider calls, no API spend.

### CLI Blocker Fixed — Proof

Before the hotfix, Typer rejected the flag with::

    No such option: --fusion-id Did you mean --run-id?

After the hotfix, the Typer registration in `loopos/cli/app.py::_typer_mad_dog` (lines 588–608) declares the `--fusion-id` option and forwards it to `mad_dog_command`, matching the underlying function surface and the `fusion-router` Typer surface.

Regression test evidence (`tests/test_fusion_router_cli.py::MadDogTyperCLIRegressionTests`, 7 tests):

| test | what it proves |
|---|---|
| `test_mad_dog_status_typer_accepts_fusion_id` | `loopos mad-dog --action status --fusion-id ID --json` is accepted by Typer; payload has `status='loaded'`, `fusion_id=<id>`; no `No such option` / `Did you mean --run-id` in output |
| `test_mad_dog_route_typer_accepts_fusion_id` | `loopos mad-dog --action route --fusion-id ID --json` is accepted by Typer; payload has `status='planning_only'`, `fusion_id=<id>`; no Typer option error |
| `test_mad_dog_status_typer_missing_fusion_id_returns_structured_error` | missing `--fusion-id` returns structured CLI error (`exit=1`, `FUSION_ID` in stderr), not a Typer option error |
| `test_mad_dog_route_typer_missing_fusion_id_returns_structured_error` | missing `--fusion-id` returns structured CLI error (`exit=1`, `--fusion-id` in stderr), not a Typer option error |
| `test_mad_dog_status_typer_unknown_fusion_id_returns_not_found` | unknown `--fusion-id` returns structured `status='not_found'` payload |
| `test_fusion_router_status_typer_still_works` | `fusion-router status --fusion-id ID` regression smoke (still passes) |
| `test_fusion_router_route_typer_planning_only_fallback` | `fusion-router route --fusion-id ID` planning-only fallback (still passes) |

All 7 regression tests pass; the full `test_fusion_router_cli.py` suite reports **23 passed** (was 16 before the hotfix — 7 new tests, no test removed).

### `rc_audit_cli_smoke.py` Result

```
[ok] fusion-router plan -> mode=single fusion_id=36e278b5-c085-4bfd-be61-cf53deadf956
[ok] fusion-router explain -> score=4 mode=single
[ok] fusion-router run --dry-run -> fusion_id=e05518ec-3ede-4c1b-9b66-5e332703ed0b
[ok] fusion-router status -> status=loaded
[ok] fusion-router list -> count=358
[ok] fusion-router route -> status=planning_only fallback=kernel_engine not supplied; returning planning-only result
[ok] mad-dog plan -> mode=mad_dog fusion_id=126bfdd2-2177-4c99-8c1f-3084ce57e2a8
[ok] mad-dog status -> status=loaded
[ok] mad-dog list -> count=359
[ok] mad-dog route -> status=planning_only fallback=kernel_engine not supplied; returning planning-only result

ALL CLI SURFACES OK
```

The `route` action's `status='planning_only'` is the desired audit behaviour: the audit harness does not wire a `kernel_engine` into the `FusionRunner`, so `route` correctly returns the structured planning-only fallback rather than executing live providers. This was already documented as known limitation #2 in the original audit and is the intended v0.2 behavior.

### Post-Hotfix Full Validation Result

```
pytest tests/test_fusion_router_cli.py -q                   -> 23 passed
pytest tests/test_fusion_router_cli.py tests/test_fusion_router_persistence.py
       tests/test_fusion_router_kernel_wiring.py
       tests/test_fusion_router_trace.py
       tests/test_fusion_router_aci_bridge.py
       tests/test_fusion_router_scoring.py
       tests/test_fusion_router_provider_selection.py
       tests/test_fusion_router_models.py
       tests/test_fusion_router_roles.py -q                  -> 102 passed
pytest tests/test_v0_2_deep_smoke.py
       tests/test_v0_2_readiness_check.py -q                 -> 41 passed
pytest -m "not slow"                                        -> 830 passed, 46 deselected, 19 subtests passed
ruff check .                                                -> All checks passed!
mypy loopos tests                                           -> Success: no issues found in 326 source files
python scripts/anti_bloat_check.py --json                   -> hard_fail_count=0, warning_count=2
python scripts/v0_2_readiness_check.py --json               -> status=pass, hard_fail_count=0
python rc_audit_cli_smoke.py                                -> ALL CLI SURFACES OK
git diff --name-only bf3b9a7..HEAD -- loopos/kernel/        -> empty
git diff --name-only bf3b9a7..HEAD -- loopos/model_kernel/  -> empty
git diff --name-only v0.1.0..HEAD -- dist/ docs/release-notes/ docs/reports/ -> empty
git status --short                                          -> M loopos/cli/app.py; M rc_audit_cli_smoke.py; M tests/test_fusion_router_cli.py (pre-commit)
```

Test count delta vs the original audit (823 → 830): **+7**, exactly the 7 new regression tests in `MadDogTyperCLIRegressionTests`. No test was removed or weakened.

### Post-Hotfix Safety Invariants

| invariant | status |
|---|---|
| No live provider API calls | PASS |
| No subprocess / shell bypass | PASS |
| No direct Policy OS bypass | PASS |
| No Syscall Router bypass | PASS |
| No hidden authority expansion | PASS |
| No automatic paid API spending | PASS |
| No release evidence mutation | PASS (dist/, docs/release-notes/, docs/reports/ empty) |
| No `v0.1.0` artifact mutation | PASS (tag untouched) |
| No kernel mutation after Phase 5 | PASS (loopos/kernel/ diff empty) |
| No `model_kernel` mutation | PASS (loopos/model_kernel/ diff empty) |
| Hotfix scope contained to CLI surface + tests | PASS (only `loopos/cli/app.py`, `tests/test_fusion_router_cli.py`, `rc_audit_cli_smoke.py` modified) |

### Post-Hotfix Final Recommendation

**Tag `v0.2.0` from the post-hotfix HEAD on `main`.**

The single RC blocker documented in the original audit (`mad-dog status` / `mad-dog route` rejecting `--fusion-id` on the Typer surface) is closed. The hotfix is the minimal, scoped change described above; no runtime, kernel, model_kernel, ACI, ALI, or Fusion logic was modified. All readiness, anti-bloat, ruff, mypy, and test gates pass. All safety invariants hold. The `v0.1.0` tag and all release evidence remain untouched.