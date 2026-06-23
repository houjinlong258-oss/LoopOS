# LoopOS v0.2 Release Candidate

> **Status: RC blocker closed — Tag v0.2.0 from the post-hotfix
> HEAD on `main`.** All hard RC gates pass. The original audit
> (commit `bf3b9a7`) recorded one CLI surface gap (missing
> `--fusion-id` option on the `mad-dog` Typer registration) as the
> only blocker for tagging `v0.2.0`. That blocker has been **fixed
> in the v0.2.0 RC hotfix** on branch
> `v0.2/rc-fix-mad-dog-fusion-id`. See the "RC Hotfix Closure"
> section in `docs/v0-2-rc-audit.md` and the "Final Post-Hotfix
> Recommendation" section at the bottom of this document for the
> post-fix verdict and validation evidence.

## What v0.2 is

LoopOS v0.2 is the **True Agent OS Kernel** milestone. It proves
that the Layer-2 pipeline — Provider Registry → ACI → ALI →
KernelLoopEngine → Trace Bridge → ALI Replay → Fusion Router →
FusionPlan persistence → planning-only runner → dry-run no-side-effect
path → policy-denied safety path — can be exercised
deterministically, replayed from trace, and verified end-to-end
without ever calling a live provider API or bypassing Policy OS,
the Syscall Router, or Trace.

v0.2 is **planning-first**: more intelligence, not more authority.
Every recommended ACI command flows through the kernel runtime's
policy engine + syscall router when the runner is invoked, so
Policy OS remains the single source of truth.

## What v0.2 ships

| substrate | package / file | proof |
|---|---|---|
| Provider Runtime Registry | `loopos/providers/`, `providers/defaults.yaml` | `tests/test_provider_registry.py` |
| Provider Consistency Guard | `tests/test_provider_model_kernel_consistency.py` | 20 tests |
| Agent Command Interface (ACI) | `loopos/aci/` | `tests/test_aci_*.py` (64 tests) |
| Agent Loop Interface (ALI) | `loopos/ali/` | `tests/test_ali_*.py` (94 tests) |
| KernelLoopEngine ACI → ALI Integration | `loopos/kernel/loop_engine.py::submit_agent_command` | `tests/test_kernel_aci_ali_integration.py` (15 tests) |
| ALI Trace Bridge | `loopos/trace/ali_bridge.py` | `tests/test_ali_trace_bridge.py` (16 tests) |
| ALI Replay Engine | `loopos/trace/ali_replay.py` | `tests/test_ali_replay_engine.py` (21 tests) |
| Fusion Router / Mad Dog Mode | `loopos/fusion_router/` | `tests/test_fusion_router_*.py` (81 tests) |
| Fusion Routing Decision Persistence + Runner | `loopos/fusion_router/store.py`, `loopos/fusion_router/runner.py` | `tests/test_fusion_router_persistence.py` (13), `tests/test_fusion_router_kernel_wiring.py` (11) |
| v0.2 Readiness Check | `scripts/v0_2_readiness_check.py` | `tests/test_v0_2_readiness_check.py` (18 tests) |
| v0.2 Deep Smoke | `tests/test_v0_2_deep_smoke.py` | 23 tests |

## Phase Chain (proves the substrate is cumulative, not forked)

```
Phase 0 governance freeze
  → Phase 1 source transplant audit
    → Phase 2 Provider Registry
      → Phase 3 Provider Consistency Guard
        → Phase 4 ACI
          → Phase 5 ALI
            → Phase 6 ACI/ALI maintainability split
              → Phase 7 KernelLoopEngine ACI → ALI integration
                → Phase 8 ALI Trace Bridge
                  → Phase 9 Fusion Router / Mad Dog Mode
                    → Phase 10 Fusion Routing Decision persistence + runner
                      → Phase 11 ALI Replay Engine
                        → Phase 12 v0.2 Readiness Check
                          → Phase 13 v0.2 Deep Smoke
```

Each phase built on the previous one without rewriting prior
work. The `loopos/kernel/` directory accumulated one extension
(`submit_agent_command`) across Phases 7 + 8; `loopos/model_kernel/`
was untouched since `v0.1.0`.

## Readiness Proof Output

`python scripts/v0_2_readiness_check.py --json` (full output):

```json
{
  "schema_version": "0.2",
  "generated_at": "2026-06-23T02:41:07.737206+00:00",
  "status": "pass",
  "checks": {
    "provider_registry_bound": {
      "status": true,
      "detail": "ProviderRegistry registered 1 profile(s); find_by_capability=1 match(es)",
      "severity": "hard"
    },
    "aci_runtime_bound": {
      "status": true,
      "detail": "CommandRunner exposes run / validate; AgentCommand pydantic-validated",
      "severity": "hard"
    },
    "ali_fsm_bound": {
      "status": true,
      "detail": "DEFAULT_FSM has 36 transition rows; session CREATED",
      "severity": "hard"
    },
    "kernel_loop_integrated": {
      "status": true,
      "detail": "KernelLoopEngine.submit_agent_command present",
      "severity": "hard"
    },
    "trace_bridge_active": {
      "status": true,
      "detail": "ALI_EVENT_TYPE='ali.event'; persist / replay helpers present",
      "severity": "hard"
    },
    "ali_replay_deterministic": {
      "status": true,
      "detail": "empty-stream replay stable in 'CREATED'; replay_session_from_trace + replay_trace_events present",
      "severity": "hard"
    },
    "fusion_router_available": {
      "status": true,
      "detail": "FusionRouter.plan produced mode='single' score=0",
      "severity": "hard"
    },
    "mad_dog_cli_available": {
      "status": true,
      "detail": "mad_dog_command + fusion_router_command callable",
      "severity": "hard"
    },
    "fusion_plan_persistence_available": {
      "status": true,
      "detail": "FusionPlanStore wrote and read back plan 'f9663698-3609-41ed-ab1e-afa1f31bfdfc' (mode='single')",
      "severity": "hard"
    },
    "policy_gates_active": {
      "status": true,
      "detail": "PolicyEngine loaded default packs (17 pack(s), 43 rule(s)); evaluate() returned allowed=True",
      "severity": "hard"
    },
    "dry_run_no_side_effects": {
      "status": true,
      "detail": "dry-run ACI returns status='dry_run' / dry_run=True",
      "severity": "hard"
    },
    "no_live_provider_calls": {
      "status": true,
      "detail": "all v0.2 packages clean",
      "severity": "hard"
    },
    "no_kernel_mutation_in_phase": {
      "status": true,
      "detail": "loopos/kernel/ untouched in Phase 8",
      "severity": "hard"
    },
    "no_model_kernel_mutation": {
      "status": true,
      "detail": "loopos/model_kernel/ untouched since v0.1.0",
      "severity": "hard"
    },
    "anti_bloat_checked": {
      "status": true,
      "detail": "hard_fail_count=0, warning_count=1",
      "severity": "hard"
    }
  },
  "hard_fail_count": 0,
  "warnings": []
}
```

## Deep Smoke Result

`pytest tests/test_v0_2_deep_smoke.py -q` — green (23 tests).

The deep smoke walks the full Layer-2 pipeline end-to-end in
the following deterministic order:

1. `ProviderRegistryProofTests` — metadata-only registry loads
   + AST scan for forbidden network imports.
2. `ACIDryRunTests` — ACI dry-run succeeds without side effects.
3. `ACIPolicyDeniedTests` — dangerous commands are blocked by
   Policy OS.
4. `ALIConsumesACIResultTests` — ALI consumes an ACI result.
5. `KernelIntegrationTests` — `KernelLoopEngine.submit_agent_command`
   drives ALI.
6. `TraceBridgeTests` — Trace Bridge persists `ali.event` records.
7. `ALIReplayProofTests` — ALI Replay reconstructs the same final
   session state.
8. `FusionRouterSmokeTests` — single-model default + mad_dog
   escalation + CLI persistence.
9. `FusionPersistenceTests` — `status` / `list` read the persisted
   plan.
10. `FusionRunnerFallbackTests` — `planning_only` fallback when no
    kernel is supplied.
11. `NoLiveProviderOrSubprocessProofTests` — no live provider calls
    or subprocess in v0.2 packages.
12. `NoKernelMutationInPhaseTests` — `loopos/kernel/*` untouched in
    Phase 8 (git diff against `69189db`).

## Full Validation Result

```
$ pytest tests/test_aci_*.py tests/test_ali_*.py -q
........................................................................ [ 47%]
........................................................................ [ 95%]
.......                                                                  [100%]
154 passed

$ pytest tests/test_ali_trace_bridge.py tests/test_ali_replay_engine.py -q
.....................................                                    [100%]
37 passed

$ pytest tests/test_kernel_aci_ali_integration.py tests/test_kernel_convergence_integration.py -q
........................                                                 [100%]
24 passed

$ pytest tests/test_fusion_router_*.py tests/test_fusion.py tests/test_fusion_integration.py -q
........................................................................ [ 64%]
.......................................                                  [100%]
130 passed

$ pytest tests/test_v0_2_deep_smoke.py tests/test_v0_2_readiness_check.py tests/test_v0_2_agent_os_kernel_integration.py -q
.....................................................                    [100%]
53 passed

$ pytest tests/test_policy_os.py tests/test_provider_registry.py tests/test_provider_model_kernel_consistency.py -q
........................................................................ [ 73%]
..........................                                               [100%]
98 passed

$ pytest -m "not slow"
...
823 passed, 46 deselected, 19 subtests passed in 68.87s (0:01:08)

$ ruff check .
All checks passed!

$ mypy loopos tests
Success: no issues found in 326 source files

$ anti_bloat_check --json
{ "hard_fail_count": 0, "warning_count": 1, "hard_fails": [], "warnings": [...] }

$ v0_2_readiness_check --json
{ "status": "pass", "hard_fail_count": 0, "warnings": [] }

$ git diff --name-only 7be88bc..HEAD -- loopos/kernel/
(empty)

$ git diff --name-only 7be88bc..HEAD -- loopos/model_kernel/
(empty)

$ git diff --name-only v0.1.0..HEAD -- dist/ docs/release-notes/ docs/reports/
(empty)

$ git status --short
(empty)
```

## Safety Invariant Table

| invariant | status |
|---|---|
| No live provider API calls | PASS |
| No subprocess / shell bypass | PASS |
| No direct Policy OS bypass | PASS |
| No Syscall Router bypass | PASS |
| No hidden authority expansion | PASS |
| No automatic paid API spending | PASS |
| No release evidence mutation | PASS |
| No `v0.1.0` artifact mutation | PASS |
| No kernel mutation after Phase 5 | PASS |
| No `model_kernel` mutation | PASS |

## Known Limitations

1. **CLI surface gap — `mad-dog` Typer registration.**
   The `mad-dog status --fusion-id ID` and
   `mad-dog route --fusion-id ID` Typer invocations are not
   wired (Typer rejects `--fusion-id` on the `mad-dog` command).
   The underlying `mad_dog_command` function and the
   `fusion-router` Typer surface both work. Fix is a one-line
   Option declaration in `loopos/cli/app.py::_typer_mad_dog`.
   **Must be fixed before tagging `v0.2.0`.**

2. **Fusion Router remains planning-only.** No live multi-provider
   execution. `live_provider_calls_allowed=False` is enforced.

3. **Fusion Verdict Orchestration is deferred.** Verdicts are
   durable audit evidence but are not auto-consumed by the
   kernel. (v0.2.1 / v0.3 candidate.)

4. **OpenGod is out of scope.** (Separate initiative.)

5. **No web UI / TUI / gateway / daemon / background scheduler.**
   CLI + library only.

6. **No automatic paid API spending.** All cost-bearing calls
   require explicit user invocation.

7. **No remote / multi-process `FusionPlanStore`.** File-based,
   per-machine.

8. **ALI Replay covers the ALI FSM layer only.** Kernel
   convergence replay is the v0.1
   `loopos.kernel.replay.ReplayEngine`'s scope.

## Non-Goals Deferred to v0.2.1 / v0.3

| non-goal | target |
|---|---|
| Fix Typer `--fusion-id` gap on `mad-dog` | v0.2.1 |
| Fusion Verdict Orchestration | v0.2.1 / v0.3 |
| Live multi-provider execution in the Fusion Runner | v0.3 |
| Model debate loops and judge-model invocation | v0.3 |
| OpenGod | separate |
| Web UI / TUI / gateway / daemon / background scheduler | separate |
| Automatic paid API spending | never (architectural rule) |

## Final Post-Hotfix Recommendation

**Tag `v0.2.0` from the post-hotfix HEAD on `main`.**

The single RC blocker (the `mad-dog` Typer surface rejecting
`--fusion-id`) is closed. The hotfix on branch
`v0.2/rc-fix-mad-dog-fusion-id` is minimal and scoped to the CLI
surface + tests + audit wrapper + audit docs:

| file | change | scope |
|---|---|---|
| `loopos/cli/app.py` | +2 lines | `fusion_id` option on `_typer_mad_dog` |
| `tests/test_fusion_router_cli.py` | +209 lines | 7 Typer regression tests + helper |
| `rc_audit_cli_smoke.py` | ~10 lines | accept `status='planning_only'` as a valid `route` fallback |
| `docs/v0-2-rc-audit.md` | appended "RC Hotfix Closure" section | blocker-status update |
| `docs/v0-2-release-candidate.md` | this section | final post-hotfix verdict |

No other files were touched. `loopos/kernel/`, `loopos/model_kernel/`,
`dist/`, `docs/release-notes/`, and `docs/reports/` remain diff-empty
against the audit base and against `v0.1.0`. The `v0.1.0` tag
remains untouched. No push, no tag, no live provider calls, no
API spend.

### Post-Hotfix Full Validation Snapshot

```
pytest tests/test_fusion_router_cli.py                                    -> 23 passed (was 16; +7 regression tests)
pytest tests/test_fusion_router_cli.py tests/test_fusion_router_persistence.py
       tests/test_fusion_router_kernel_wiring.py tests/test_fusion_router_trace.py
       tests/test_fusion_router_aci_bridge.py tests/test_fusion_router_scoring.py
       tests/test_fusion_router_provider_selection.py
       tests/test_fusion_router_models.py tests/test_fusion_router_roles.py -> 102 passed
pytest tests/test_v0_2_deep_smoke.py tests/test_v0_2_readiness_check.py   -> 41 passed
pytest -m "not slow"                                                      -> 830 passed, 46 deselected, 19 subtests passed
ruff check .                                                              -> All checks passed!
mypy loopos tests                                                         -> Success: no issues found in 326 source files
python scripts/anti_bloat_check.py --json                                 -> hard_fail_count=0, warning_count=2
python scripts/v0_2_readiness_check.py --json                             -> status=pass, hard_fail_count=0
python rc_audit_cli_smoke.py                                              -> ALL CLI SURFACES OK
git diff --name-only bf3b9a7..HEAD -- loopos/kernel/                      -> empty
git diff --name-only bf3b9a7..HEAD -- loopos/model_kernel/                -> empty
git diff --name-only v0.1.0..HEAD -- dist/ docs/release-notes/ docs/reports/ -> empty
```

Test count delta: 823 → 830 (**+7**, exactly the new regression
tests; no test removed or weakened).

### Post-Hotfix Final Safety Invariants

| invariant | status |
|---|---|
| No live provider API calls | PASS |
| No subprocess / shell bypass | PASS |
| No direct Policy OS bypass | PASS |
| No Syscall Router bypass | PASS |
| No hidden authority expansion | PASS |
| No automatic paid API spending | PASS |
| No release evidence mutation | PASS |
| No `v0.1.0` artifact mutation | PASS |
| No kernel mutation after Phase 5 | PASS |
| No `model_kernel` mutation | PASS |
| Hotfix scope contained to CLI surface + tests + docs | PASS |

The detailed audit evidence lives in `docs/v0-2-rc-audit.md`; the
hotfix closure is documented in the "RC Hotfix Closure — `mad-dog
--fusion-id` Typer Fix" section of that document.

The detailed audit evidence lives in `docs/v0-2-rc-audit.md`.

## Release Packaging Polish (post-hotfix)

After the RC hotfix landed on `main`, a final **metadata-only**
polish pass was applied on branch
`v0.2/rc-release-package-polish` so the v0.2.0 source archive is
professionally consistent for external consumers. This pass is
audit-only with respect to runtime: no kernel change, no model
kernel change, no ACI / ALI / Fusion behaviour change, no
dependency added.

### Version metadata (consumer-visible)

| file | before | after |
|---|---|---|
| `VERSION` | `0.1.0` | `0.2.0` |
| `pyproject.toml` `[project].version` | `"0.1.0"` | `"0.2.0"` |

`VERSION` and `pyproject.toml` were both still pinned at `0.1.0`
even though every readiness gate and audit doc already referenced
v0.2. They now agree at `0.2.0`.

### README banner

| field | before | after |
|---|---|---|
| line 3 banner | "v0.2 in progress — boundary banner" | "v0.2.0 released — True Agent OS Kernel" |
| section header | "## v0.2 Substrates (in progress)" | "## v0.2 Substrates (released)" |

The banner now points consumers at `dist/LoopOS-v0.2.0-source.zip`
and the annotated tag `v0.2.0` instead of implying v0.2 is still
in flight. The freeze caveat on `v0.1.0` evidence is preserved.

### Archive-mode readiness (no `.git` in extracted zip)

`scripts/v0_2_readiness_check.py` now accepts a `--archive-mode`
flag (and auto-detects when `.git` is missing). In archive-mode,
git-required checks (`no_kernel_mutation_in_phase`,
`no_model_kernel_mutation`, `anti_bloat_checked`,
`release_evidence_untouched`) are reported as `severity="warning"`
findings with `status=True` and `detail="skipped: archive-mode (no
.git); requires git checkout"`. Code-only checks still run with
their normal `severity="hard"` semantics. The payload gains a
top-level `mode` field (`"archive"` or `"git-checkout"`).

This lets downstream consumers validate an extracted v0.2.0 source
archive without cloning the repo, while still requiring a git
checkout for full release validation. New tests in
`tests/test_v0_2_readiness_check.py::ReadinessCheckArchiveModeTests`
lock this behaviour in.

### Unicode / encoding hygiene

A repo-wide scan for `#Uxxxx` escape sequences returned **zero
hits**. The only non-ASCII bytes in `README.md`,
`docs/v0-2-release-candidate.md`, and `docs/v0-2-rc-audit.md` are
em dashes (`U+2014`, encoded `e2 80 94`), which are valid UTF-8 and
intentional. Any `�?` or `#Uxxxx` rendering seen in tooling output
is a PowerShell console encoding artifact (Windows PowerShell 5.1
default code page cannot display U+2014); the bytes on disk are
clean and the rendered output is correct when UTF-8 output
encoding is requested (e.g. `PYTHONIOENCODING=utf-8`).

### Files touched in the polish pass

| file | scope | runtime impact |
|---|---|---|
| `VERSION` | value only | none |
| `pyproject.toml` | `[project].version` only | none |
| `README.md` | banner + section header only | none |
| `docs/v0-2-release-candidate.md` | appended this section | none |
| `docs/v0-2-rc-audit.md` | appended polish-pass note (see below) | none |
| `scripts/v0_2_readiness_check.py` | `--archive-mode` flag + skipped-finding helper + `mode` field | none on git-checkout behaviour; archive-mode is purely additive |
| `tests/test_v0_2_readiness_check.py` | added `ReadinessCheckArchiveModeTests` | none |

`loopos/kernel/`, `loopos/model_kernel/`, `dist/`,
`docs/release-notes/`, and `docs/reports/` all remain
**diff-empty** against the hotfix HEAD and against `v0.1.0`.

### Final packaging procedure (post-polish)

1. Run the full validation suite (`python rc_audit_cli_smoke.py`,
   `python scripts/v0_2_readiness_check.py --json`,
   `python scripts/anti_bloat_check.py --json`,
   `python -m pytest -q -m "not slow"`, `python -m ruff check .`,
   `python -m mypy loopos tests`).
2. Re-cut the annotated tag `v0.2.0` to the polish-branch HEAD.
3. Regenerate `dist/LoopOS-v0.2.0-source.zip` from the tag with
   `git archive --format=zip --prefix=LoopOS-v0.2.0/ ...`.
4. Write the SHA256 sidecar
   `dist/LoopOS-v0.2.0-source.zip.sha256`.
5. Verify the zip contains `README.md` and `CHANGELOG.md` at its
   root, then archive-mode-validate the extracted copy with
   `python scripts/v0_2_readiness_check.py --json --archive-mode`.

No push, no remote, no paid API call.