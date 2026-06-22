# LoopOS v0.2 Readiness Proof

> **Phase 8 deliverable.** This document describes what the
> v0.2 release-candidate proves, what it does not yet do, the
> deep-smoke scenario that exercises the full pipeline, the
> deterministic replay proof, the Fusion Router proof, the
> safety invariants the proof enforces, and the remaining
> limitations that defer to v0.3+.

## What v0.2 Proves

The v0.2 RC proof loop demonstrates that LoopOS v0.2 can
deterministically exercise and verify the full Layer-2 pipeline:

```
Provider Registry
  -> ACI
  -> ALI
  -> KernelLoopEngine.submit_agent_command
  -> Trace Bridge
  -> ALI Replay (deterministic rebuild)
  -> Fusion Router / Mad Dog Mode planning
  -> FusionPlan persistence
  -> FusionRunner planning-only fallback
  -> Policy-denied safety path
  -> dry-run no-side-effect path
```

The proof is delivered as:

1. **ALI Replay Engine** (`loopos/trace/ali_replay.py`) -- reads
   persisted ``ali.event`` records from the existing
   :class:`TraceStore` and rebuilds a fresh
   :class:`AgentLoopSession` by re-applying events through the
   existing :class:`AgentLoopFSM`. Same ordered event stream
   always yields the same final session state.
2. **Deep Smoke Test** (`tests/test_v0_2_deep_smoke.py`) --
   exercises every step of the pipeline end-to-end and asserts
   the proof matrix the master prompt mandates.
3. **Readiness Check Script** (`scripts/v0_2_readiness_check.py`)
   -- emits a structured JSON document confirming all 15
   readiness checks pass on the v0.2 repo state.
4. **Documentation** (this file) -- records what is proven, what
   is deferred, and the safety invariants the proof enforces.

## What v0.2 Does Not Yet Do

v0.2 is a **planning-first** release. The following capabilities
are explicitly deferred:

- Live multi-provider fanout (the Fusion Router is
  planning-only; ``live_provider_calls_allowed=False`` is
  enforced).
- Model debate loops, automatic paid API spending.
- Web UI, TUI, gateway, daemon, background scheduler.
- Fusion Verdict Orchestration (deferred to v0.2.1 / v0.3).
- OpenGod (a separate, larger initiative).
- ACP / external API integration.

The v0.2 RC is meant to be the **proof surface** for the v0.2
architecture, not the v0.2 production runtime.

## Deep Smoke Scenario

The deep smoke test (`tests/test_v0_2_deep_smoke.py`) walks
the full pipeline in 23 deterministic tests:

| step | test class | what it proves |
|---|---|---|
| 1 | `ProviderRegistryProofTests` | metadata-only registry loads + AST scan for forbidden network imports |
| 2 | `ACIDryRunTests` | ACI dry-run succeeds without side effects |
| 3 | `ACIPolicyDeniedTests` | dangerous commands are blocked by Policy OS |
| 4 | `ALIConsumesACIResultTests` | ALI consumes an ACI result |
| 5 | `KernelIntegrationTests` | `KernelLoopEngine.submit_agent_command` drives ALI |
| 6 | `TraceBridgeTests` | Trace Bridge persists `ali.event` records |
| 7 | `ALIReplayProofTests` | ALI Replay reconstructs the same final session state |
| 8 | `FusionRouterSmokeTests` | single-model default + mad_dog escalation + CLI persistence |
| 9 | `FusionPersistenceTests` | `status` / `list` read the persisted plan |
| 10 | `FusionRunnerFallbackTests` | `planning_only` fallback when no kernel is supplied |
| 11 | `NoLiveProviderOrSubprocessProofTests` | no live provider calls or subprocess in v0.2 packages |
| 12 | `NoKernelMutationInPhaseTests` | `loopos/kernel/*` untouched in Phase 8 (git diff against `69189db`) |

## Replay Proof

The ALI Replay Engine (`loopos/trace/ali_replay.py`) is the
**deterministic replay proof surface**. It:

- Reads ``ali.event`` records from the existing
  :class:`loopos.kernel.trace.TraceStore`.
- Rebuilds a fresh :class:`AgentLoopSession` from the ordered
  event stream.
- Re-applies events through the existing :class:`AgentLoopFSM`.
- Does **not** re-run ACI, Policy OS, or Syscall Router.
- Does **not** call providers or run subprocesses.
- Is deterministic: same ordered event stream -> same final
  session state.

The replay test surface (`tests/test_ali_replay_engine.py`,
21 tests) covers:

- Single-event sessions.
- Happy-path sessions ending in HALTED_SUCCESS.
- Policy-denied sessions ending in HALTED_BLOCKED.
- Approval-required sessions ending in WAITING_APPROVAL.
- Repairable failure sessions ending in REPAIRING.
- Unsupported-command sessions ending in HALTED_FAILURE.
- Replanning sessions ending in REPLANNING.
- Roundtrip through the trace store.
- Determinism across runs.
- Dropped-event accounting (out-of-order, unknown events,
  post-terminal events).

## Fusion Router Proof

The deep smoke test (`tests/test_v0_2_deep_smoke.py`) exercises
the Fusion Router proof matrix:

| trigger / scenario | expected mode | proven by |
|---|---|---|
| trivial typo fix, low score | `single` | `test_router_defaults_to_single_for_low_score_task` |
| nasty release blocker, `explicit_user_request` from user | `mad_dog` | `test_router_escalates_to_mad_dog_on_user_trigger` |
| `mad-dog plan task.json` CLI invocation | persists plan, `status` returns `loaded`, `mode=mad_dog` | `test_mad_dog_cli_command_persists_plan` |
| `fusion-router plan task.json` low-score | persists plan, `status` returns `loaded`, `mode=single` | `test_plan_persists_and_status_list_read_it` |
| `fusion-router status` for unknown id | returns `not_found` payload | `test_status_not_found_payload` |
| `FusionRunner.run(plan)` with no kernel engine | returns `status=planning_only` | `test_runner_returns_planning_only_without_kernel` |

Fusion Router remains **planning-only**: every recommended ACI
command flows through the kernel runtime's policy engine +
syscall router when the runner is invoked, so Policy OS remains
the single source of truth. No live provider calls are made.

## Safety Invariants

The v0.2 RC proof enforces the following safety invariants:

1. **No live provider API calls.** The v0.2 packages
   (`loopos/providers`, `loopos/aci`, `loopos/fusion_router`,
   `loopos/trace`) are AST-scanned for `requests`, `httpx`,
   `urllib.request`, and `urllib3` imports. A failure aborts
   the readiness check.
2. **No direct subprocess / shell bypass.** The same AST scan
   flags `subprocess` / `popen` imports. The runner adapter uses
   the kernel runtime's syscall router, never raw `os.system`.
3. **No `loopos/kernel/*` mutation in Phase 8.** The readiness
   check runs `git diff <PHASE_8_BASE>..HEAD -- loopos/kernel/`
   against the Phase 7 base commit `69189db`. The diff must be
   empty.
4. **No `loopos/model_kernel/*` mutation since v0.1.0.** The
   readiness check runs `git diff <v0.1.0>..HEAD -- loopos/model_kernel/`.
   The diff must be empty.
5. **No release-evidence mutation.** The readiness check runs
   `git diff <v0.1.0>..HEAD -- dist/ docs/release-notes/ docs/reports/`.
   The diff must be empty.
6. **Dry-run ACI does not produce side effects.** A dry-run
   command must return `status='dry_run'` and `dry_run=True`
   without touching the filesystem outside the kernel's `.loopos/`
   data dir.
7. **Policy OS gates are active.** The default policy pack loads
   and a real `PolicyEngine.evaluate(...)` call returns a typed
   decision with `allowed` attribute.
8. **Anti-bloat gate clean.** `python scripts/anti_bloat_check.py --json`
   must report `hard_fail_count=0`.

## Remaining Limitations

The v0.2 RC is the proof loop, not the production runtime:

- **No live multi-provider execution.** The Fusion Router is
  planning-only; only ACI / Kernel / Syscall Router can execute
  governed commands.
- **No Fusion Verdict Orchestration.** Verdicts are durable
  audit evidence but are not auto-consumed by the kernel. This
  is a v0.2.1 / v0.3 candidate (`v0.2/phase-8-fusion-verdict-orchestration`
  per the master prompt's deferral note).
- **No OpenGod.** The broader multi-agent orchestration
  initiative is a separate, larger effort.
- **No web UI / TUI / gateway / daemon / background scheduler.**
  CLI + library only.
- **No automatic paid API spending.** All cost-bearing calls
  require explicit user invocation.
- **No remote / multi-process FusionPlanStore.** The store is
  file-based and per-machine; concurrent writers from multiple
  processes are not safe.
- **Replay covers the ALI FSM layer only.** Kernel convergence
  is not replayed; that is the v0.1
  `loopos.kernel.replay.ReplayEngine`'s scope.
- **No model-debate loops or judge models.** The Fusion Router
  plans role assignments but never invokes them in v0.2.

## How to Re-run the Proof

```bash
# 1. Run the deep smoke test
python -m pytest tests/test_v0_2_deep_smoke.py -q

# 2. Run the ALI replay engine tests
python -m pytest tests/test_ali_replay_engine.py -q

# 3. Run the readiness check script
python scripts/v0_2_readiness_check.py --json

# 4. Re-run the readiness check tests
python -m pytest tests/test_v0_2_readiness_check.py -q

# 5. Run the full v0.2 test suite
python -m pytest -q -m "not slow"
```

A successful proof produces:

- 23 deep-smoke tests + 21 replay-engine tests + 18
  readiness-check tests, all green.
- `readiness.status == "pass"` with `hard_fail_count == 0`.
- `anti_bloat` reports `hard_fail_count=0`.
- Working tree clean (no uncommitted changes).
- `git diff` over `loopos/kernel/`, `loopos/model_kernel/`,
  `dist/`, `docs/release-notes/`, `docs/reports/` is empty.

## Audit Trail Summary

| artefact | path | role |
|---|---|---|
| ALI Replay Engine | `loopos/trace/ali_replay.py` | deterministic replay proof surface |
| Deep Smoke Test | `tests/test_v0_2_deep_smoke.py` | full pipeline end-to-end proof |
| ALI Replay Engine Tests | `tests/test_ali_replay_engine.py` | replay-specific proofs |
| Readiness Check Script | `scripts/v0_2_readiness_check.py` | structured JSON readiness proof |
| Readiness Check Tests | `tests/test_v0_2_readiness_check.py` | readiness-script regression tests |
| This Document | `docs/v0-2-readiness.md` | release-readiness evidence |

The v0.2 RC is **planning-first**: more intelligence, not more
authority. Every capability that the proof exercises still
flows through Policy OS + Syscall Router + Trace Bridge + the
existing kernel convergence engine. No new runtime authority is
introduced.