# LoopOS v0.2 Release Candidate

> **Status: RC pending one CLI fix.** All hard RC gates pass.
> One CLI surface gap (missing `--fusion-id` option on the
> `mad-dog` Typer registration) is the only blocker for tagging
> `v0.2.0`. See `docs/v0-2-rc-audit.md` for the full audit
> record.

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

## Final Recommendation

**Do not tag `v0.2.0` yet.** The audit base is clean and all
hard gates pass, but the `mad-dog` Typer surface must be wired
for `--fusion-id` before the tag.

**Once that fix lands:**

1. Apply the one-line Option declaration to `_typer_mad_dog`.
2. Add a regression test in `tests/test_fusion_router_cli.py`.
3. Re-run `rc_audit_cli_smoke.py`, `pytest -m "not slow"`,
   `ruff`, `mypy`, `anti_bloat_check`, `v0_2_readiness_check`.
4. Tag `v0.2.0` from the resulting HEAD.

The detailed audit evidence lives in `docs/v0-2-rc-audit.md`.