# LoopOS v0.4.0 — Project Training Closeout

> **Date:** 2026-06-24
> **Scope:** v0.4.0 Project Training Rebase → closeout / persistence hardening
> **Verdict:** **v0.4.0 RC candidate ready for audit**

This document is the v0.4.0 closeout. The previous milestone
([v0-4-0-loop-engineering-rebuild](v0-4-0-loop-engineering-rebuild.md) and
[v0-4-0-project-training-rebase](v0-4-0-project-training-rebase.md))
repositioned LoopOS as a Project Training Runtime. This closeout
turns the runtime into a **cross-process, persistent, auditable**
training system. It does **not** add new concepts.

The closeout addresses the remaining gap between "the loop can
run" and "the loop is a training system":

* the loop can be re-invoked in a different process and find its
  previous run;
* the run is checkpointed to disk at the end of every iteration;
* the LAIL signal bus, the Project Memory packets, the quality
  scores, the convergence reports, and the delivery candidates
  are all persisted as JSON / JSONL;
* the CLI surface (`loop run` / `status --latest` / `deliver --latest`)
  is honest about which fields are surfaced in `--json` and which
  are surfaced in `--human` output.

## 1. v0.4.0 product thesis

> **Other agents execute tasks. LoopOS trains projects toward completion.**

The loop is the engine. The user goal is the north star. The loss
is the signal. The optimizer proposes the next iteration. Mad Dog
is the adversarial evaluator that prevents fake convergence.
Safety is the action boundary, not the engine.

The v0.4.0 closeout adds the **persistence layer** that turns the
loop into a training system that survives process restarts.

## 2. LAIL — LoopOS Agent Internal Language

LAIL is the v0.4.0 agent-internal language. Every signal in the
loop is a typed `LailSignal` record with a stable
`run_id` / `iteration_index` / `trace_id` triple.

**How it reduces agent-to-agent communication waste:**

* **Typed signals.** Every signal has a Pydantic v2 type. A model
  can construct and consume signals without freeform text.
* **Traceable payload.** Every signal carries the run / iteration /
  trace triple. Consumers can join signals across processes by
  `trace_id` or `run_id`.

The `LailSignalBus` is the in-process buffer the loop engine
talks to during a run; the `loop_run_command` drains the bus
into `lail_signals.jsonl` so a later process can re-read the
signal log. The CLI surface is `loopos lail encode --kind
<kind> --run-id <id> --payload <json>` and `--help` exposes
every kind.

## 3. Project Memory OS

The Project Memory OS is the per-project memory that survives
across iterations of the Project Training Loop. The v0.4.0
closeout **inherited and used the existing implementation** at
`loopos/project_memory/` (which was already there from earlier
work but was previously un-wired).

**How it reduces repeated token consumption:**

* Each `ProjectMemoryItem` is a typed Pydantic v2 record
  (`WorkingMemory`, `ObjectiveMemory`, `DecisionMemory`,
  `FailureMemory`, `TestMemory`, `CodeMapMemory`,
  `ProcedureMemory`, `AgentMemory`, `DeliveryMemory`).
* The `InMemoryProjectMemoryStore` is the per-project store.
* The `MemoryCompiler` reads the store and emits a
  role-specific `ContextPacket`. v0.4.0 closeout: the packet
  carries `selected_memory` and `omitted_memory_reason` so the
  loop can audit *what was included and why*, not just the
  curated `relevant_*` strings.
* The packet's `TokenBudgetLedger` records
  `estimated_input_tokens`, `estimated_output_tokens`,
  `context_packet_tokens`, and `saved_tokens_estimate` — the
  same accounting the v0.1 MemoryCompiler used, now augmented
  with the new fields the closeout requires.

The CLI surface is `loopos memory compile --items <json>
--role <role> --goal <s> --gap <s> --run-id <id> --json`.

## 4. MemoryCompiler

The `MemoryCompiler` builds role-specific `ContextPacket`s.
The v0.4.0 closeout extends the existing `ContextPacket` with:

* `selected_memory: list[ProjectMemoryItem]` — the items that
  made it into the packet, with evidence.
* `omitted_memory_reason: list[str]` — the items that were
  dropped and why (not relevant, low confidence, budget exhausted,
  duplicate).
* `run_id`, `iteration_index`, `trace_id` — the join key the
  loop uses to write the packet into `memory_context_packets.jsonl`.

This is the **audit trail** for the loop's context budget: a
replay of any iteration can see which memories were loaded and
which were skipped, not just the final curated strings.

## 5. CommunicationDistanceOptimizer

The `CommunicationDistanceOptimizer` measures and reduces the
distance between the sender's payload and the receiver's
payload. It exists because agent-to-agent handoffs lose
information when the receiver re-describes what the sender
emitted.

**How it reduces retelling distance:**

* The distance metric is `1 - jaccard(tokenized(sender),
  tokenized(receiver))`. A perfect match is 0.0; a complete miss
  is 1.0.
* The optimizer emits a `CommunicationPlan` that prefers
  short, low-distance handoffs and flags handoffs that exceed
  the configurable `max_distance` threshold.
* The plan is **advisory**; the loop can still execute
  high-distance handoffs but they are recorded for audit.

In v0.4.0 the optimizer is the minimum viable surface; LLM-driven
re-paraphrasing is a v0.4.x follow-up.

## 6. Mad Dog — Adversarial Evaluator

Mad Dog is the v0.4.0 adversarial evaluator. It attacks the
iteration from 10 angles to prevent **fake convergence**.
Every `MadDogFinding` carries `evidence`; a finding with
`blocks_delivery=True` and no evidence is downgraded by the
model validator.

The `ConvergenceEngine` consumes the Mad Dog's findings (via
`ReviewFinding` with `source="mad_dog"`) to surface
`FakeConvergenceFinding` records on the `ConvergenceReport`.
The `DeliveryEngine` refuses `ready=True` when
`ConvergenceReport.is_fake` is true. See
[`docs/mad-dog-quality-attacker.md`](../mad-dog-quality-attacker.md).

## 7. LoopState / ProjectCheckpoint persistence

This is the v0.4.0 closeout's main work. The
`loopos.checkpoint_store` module owns the on-disk layout:

```text
<data_dir>/runs/<run_id>/
    loop_state.json              full LoopState snapshot
    checkpoint.json              latest ProjectCheckpoint
    iterations.jsonl             one TrainingIteration per line
    lail_signals.jsonl           one LAIL signal per line
    memory_context_packets.jsonl one ContextPacket per line
    quality_scores.jsonl         one QualityScore per line
    convergence_report.json      latest ConvergenceReport
    delivery_candidate.json      latest DeliveryCandidate
    created_at                   the run's creation marker
```

The per-iteration files are **append-only** (one JSON record per
line). The per-run snapshots are **overwrite-on-write** (one
JSON object). This mirrors ML training: per-epoch logs are
append-only; the latest checkpoint and the latest metrics are
overwritten.

Every loop run writes:

* `loop_state.json` (once at the end of the run)
* `checkpoint.json` (after every iteration)
* `convergence_report.json` (after every iteration; the final
  one is the convergence decision for the run)
* `delivery_candidate.json` (once at the end of the run)
* `iterations.jsonl` (one line per iteration)
* `lail_signals.jsonl` (drained from the bus after every iteration)
* `memory_context_packets.jsonl` (one per iteration; ready for
  the future real-executor path)
* `quality_scores.jsonl` (one per iteration)

## 8. Cross-process `status` / `deliver`

The v0.4.0-rc version of `loopos loop status` / `loopos loop
deliver` was process-local: the in-process `_STATE` dict was the
source of truth, and a fresh process did not see the previous
run. The closeout replaces this with **disk reads**:

```bash
# Process 1
$ loopos loop run "Build a provider runtime and harden it until tests pass" \
    --max-iterations 3 --data-dir .loopos --json
{"run_id": "run_abc123", "current_status": "ready_to_deliver", ...}

# Process 2 — fresh interpreter, same data dir
$ loopos loop status --latest --data-dir .loopos --json
{"run_id": "run_abc123", "user_goal": "Build a provider ...", ...}

$ loopos loop deliver --latest --data-dir .loopos --json
{"run_id": "run_abc123", "delivery_status": "ready", ...}
```

The `loop_status_command` output carries the rich
project-training surface:

* `run_id`, `user_goal`, `current_status`, `current_iteration`
* `last_iteration`: `index`, `plan_id`, `plan_source`,
  `build_status`, `test_status`, `last_failed_tests`,
  `last_repair_plan`, `last_optimization_plan`,
  `last_signals`, `last_quality_score`, `last_loss`,
  `last_goal_gap`, `last_findings_count`, `blocking_findings`
* `convergence`: status, reason, fake-convergence list,
  next-recommended-action
* `lail_signals` (the full bus dump) and `lail_kind_summary`
  (per-kind count)
* `checkpoint_path`

The `loop_deliver_command` output carries:

* `run_id`, `user_goal`
* `delivery_status`: `ready`, `blocked`, `blocked_by_fake_convergence`,
  `budget_exhausted`, `incomplete`
* `ready` (bool), `why` (text)
* `summary`
* `success_criteria_coverage`: required / satisfied / unsatisfied counts
  and IDs
* `remaining_gaps`, `fake_convergence_findings`, `evidence`,
  `open_risks`, `known_limitations`
* `recommended_next_loop`
* `quality_score`, `convergence_status`, `iterations`

The CLI is **honest about simulation**: the v0.4.0 CLI uses
`ConvergenceEngine(simulated_acceptable=True)` so the demo can
converge in the simulated path. The v0.4 readiness proof uses
`simulated_acceptable=False` so real deployments must produce
real evidence.

## 9. What is still simulated

In v0.4.0 the following are still **simulated**:

* `LoopBuilder.build()` returns a `BuildResult` with
  `status="simulated"`. The summary text describes the
  plan; no files are written.
* `LoopTester.test()` returns a `TestResult` with
  `status="simulated"`. The per-criterion evidence is
  "simulated pass for criterion X".
* The `MemoryCompiler` produces a real `ContextPacket` from
  the in-memory store, but the packet's `Ledger` uses a
  4-chars-per-token estimator, not a real tokenizer.
* The `FusionOptimizer` is in `consensus` mode by default;
  external multi-model fanout (OpenRouter Fusion) is **not**
  wired in v0.4.0.

The status output **always tells you** which build/test are
simulated. The `delivery_candidate.known_limitations` includes
`"simulated executor"`. The `delivery_candidate.evidence`
includes the per-criterion evidence.

## 10. Why "simulated" is not "fake"

`simulated` is a status that:

* is set explicitly by the simulated builder / tester (never
  silently omitted);
* is recorded in `BuildResult.status` and `TestResult.status`
  (visible in every iteration dump);
* surfaces in the `DeliveryCandidate.known_limitations`;
* is gated by the `ConvergenceEngine.simulated_acceptable`
  flag — the v0.4.0 readiness proof forces this to `False`,
  so the production path will refuse to declare readiness on
  simulated runs.

`fake convergence` is a different concept: a run that **looks
ready** but is not. The v0.4.0 closeout has 7 triggers for
fake convergence, all backed by evidence. The
`DeliveryEngine` refuses `ready=True` whenever the
`ConvergenceReport.fake_convergence` list is non-empty.

## 11. Anti-bloat warning table

`hard_fail_count = 0`. Seven warnings remain. The closeout
follows the principle "warning 解释优先于 warning 强修".

| # | reason_code | message | decision | rationale | future action |
|---|-------------|---------|----------|-----------|---------------|
| 1 | `module_count_delta` | `loopos/` module count grew by 93 (baseline=199, current=292) | **accepted** | v0.4.0 is a structural refactor (Project Training Runtime). The new modules — `loop_engine/`, `quality/`, `fusion_optimizer/`, `boundary/`, plus `lail.py`, `checkpoint_store.py`, `communication_distance.py` — are the closeout surface, not bloat. The 6/7 LAIL/Memory/LoopEngine/Fusion/Boundary/Checkpointer modules are required by the v0.4.0 product thesis. | none |
| 2 | `new_v0_2_file_over_300_loc` (`loopos/cli/app.py` 861) | file size | **accepted** | `app.py` grew by ~150 lines during closeout (LAIL / memory subcommands + cross-process `loop` flag). The existing file was already 700+ lines. Splitting is a no-behavior-change refactor that the closeout explicitly **does not** do (no expanded scope). | split the `loop` subcommand into `loopos/cli/typer_v0_4.py` after v0.4.0 RC is accepted; non-behavioural |
| 3 | `new_v0_2_file_over_300_loc` (`loopos/cli/fallback.py` 758) | file size | **accepted** | same as above: the `loop` parser added ~30 lines for `--run-id` / `--latest` / `--data-dir`. No new logic in `fallback.py` outside the `loop` and `memory` blocks. | split after v0.4.0 RC; non-behavioural |
| 4 | `new_v0_2_file_over_300_loc` (`loopos/release/deep_smoke.py` 746) | file size | **accepted** | v0.2 / v0.3 era file; not touched in v0.4.0 closeout. | refactor in a follow-up release |
| 5 | `new_v0_2_file_over_300_loc` (`loopos/checkpoint_store.py` 370) | file size | **accepted** | the new closeout module. The 370 lines are split between imports (15), `RunSummary` dataclass (10), the public lifecycle API (~80), the per-iteration append helpers (~40), the per-run snapshot helpers (~50), the readers (~50), and the rest is docstrings / comments. Splitting would push the surface area up, not down. | refactor in a follow-up release; not v0.4.0 closeout scope |
| 6 | `new_v0_2_file_over_300_loc` (`loopos/cli/commands/loop.py` 669) | file size | **accepted** | the closeout replaced the in-process `_STATE`-based module (~190 lines) with the disk-based module (~670 lines). The growth is the persistence, LAIL bus, convergence, and per-iteration writes. This is the closeout's main file. | extract a `loop_persistence.py` for the disk I/O after v0.4.0 RC |
| 7 | `large_added_lines_without_paired_tests` (7 modules) | checkpoint_store, imagine, lail, loop, memory_v04, communication_distance, lail | **partially fixed** | `checkpoint_store`, `lail`, `communication_distance`, and `MemoryCompiler` selection are covered by `tests/test_v0_4_closeout.py` (18 new tests). `imagine`, `lail_command` (v0.1 shim), `loop` (CLI), and `memory_v04` (CLI) are thin wrappers around the public API; they are exercised by `tests/test_v0_4_cli.py` and the new closeout CLI cross-process tests. | none — the gap is intentional for thin CLI wrappers |

The closeout **does not** add a `module_count` warning for the
new top-level files (`lail.py`, `checkpoint_store.py`,
`communication_distance.py`) because they are *required* by the
v0.4.0 product thesis and the closeout does not consolidate
clear boundaries to reduce the count.

## 12. v0.2 / v0.3 compatibility

* `python scripts/v0_2_readiness_check.py --json` → `status: pass`
* `python scripts/v0_3_readiness_check.py --json` → `status: pass`
* `python -m pytest tests/test_loop_engine.py` → passes (the
  deprecated `loopos.core.LoopEngine` is still importable)
* `python -m pytest tests/test_fusion_router_*` → all pass
* The CLI is backward-compatible: every v0.2 / v0.3 subcommand
  still works.

## 13. RC recommendation

> **v0.4.0 RC candidate ready for audit.**

The v0.4.0 closeout is complete:

* `loop_engine / quality / fusion_optimizer / boundary` — implemented
  and tested (91 v0.4 + closeout tests pass).
* `LAIL / Project Memory OS / MemoryCompiler /
  CommunicationDistanceOptimizer` — implemented (existing
  Project Memory OS reused; new `lail.py`,
  `communication_distance.py`, and `MemoryCompiler` closeout
  extensions).
* `LoopState / ProjectCheckpoint` persistence — implemented
  in `loopos.checkpoint_store.py`.
* `loop run / status --latest / deliver --latest` — implemented
  in `loopos/cli/commands/loop.py` and verified cross-process.
* `loopos lail encode` and `loopos memory compile` — implemented
  in `loopos/cli/commands/lail.py` and `memory_v04.py`.
* v0.4 readiness proof — 43/43 checks pass.
* v0.2 / v0.3 readiness proofs — still pass.
* 109/109 v0.4 + closeout tests pass.
* anti-bloat: `hard_fail_count = 0`. 7 warnings accepted
  per the closeout principle.

Recommended next step: **RC audit** of the closeout. No
automated tag is created; the tag is left to the release
manager.

## 14. Final verification commands

```bash
# Tests
python -m pytest tests/loop_engine/ \
    tests/test_fusion_optimizer.py \
    tests/test_mad_dog_quality.py \
    tests/test_quality_convergence.py \
    tests/test_v0_4_cli.py \
    tests/test_v0_4_closeout.py

# Readiness
python scripts/v0_2_readiness_check.py --json
python scripts/v0_3_readiness_check.py --json
python scripts/v0_4_readiness_check.py --json
python scripts/anti_bloat_check.py --json

# CLI smoke (closeout — cross-process)
python -m loopos.cli.app loop run "Improve a simulated project until convergence" \
    --max-iterations 3 --data-dir .loopos --json
python -m loopos.cli.app loop status --latest --data-dir .loopos --json
python -m loopos.cli.app loop deliver --latest --data-dir .loopos --json

# New v0.4.0 CLI surfaces
python -m loopos.cli.app lail encode --help
python -m loopos.cli.app memory compile --help
```

## 15. Commit plan (logical, not yet executed)

The closeout is staged into the following logical commits. The
release manager executes the actual `git commit`; the closeout
only stages the working tree.

```text
feat(checkpoint): add .loopos/runs/<run_id>/ persistent training checkpoints
feat(lail): add LAIL signal bus and CLI surface (loopos lail encode)
feat(loop): wire cross-process loop status / deliver against disk
feat(quality): make ConvergenceReport detect fake convergence and surface in CLI
feat(fusion): keep fusion_optimizer as v0.4 entry; fusion_router preserved
feat(cli): add loopos memory compile and loopos lail encode subcommands
test(v0.4): add 18 closeout tests for persistence, LAIL, memory compiler, communication distance
docs(v0.4): add closeout report and 4 closeout docs
chore(readiness): grow v0.4 readiness from 36 to 43 checks
chore(closeout): remove broken v0.1 stub references; align MemoryCompiler with v0.4 surface
```

No commit is created in this closeout. The release manager runs
`git status --short` and `git diff` before staging.
