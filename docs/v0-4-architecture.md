# v0.4 Architecture

> LoopEngine (product) → KernelLoopEngine (execution) → Syscall/Policy (boundary).

This document is the v0.4.0 layering map. It tells you which module
owns which concern, and where the boundaries are.

## 1. Layers, top to bottom

```text
┌──────────────────────────────────────────────────────────────┐
│  Product Layer (v0.4.0 — new)                                  │
│    loop_engine/, quality/, fusion_optimizer/, boundary/        │
├──────────────────────────────────────────────────────────────┤
│  Execution Backend (v0.2 / v0.3 — preserved)                  │
│    kernel/, ail/, execution/, agent_bus/, aci/, ali/          │
│    cli_ui/, workbench/                                        │
├──────────────────────────────────────────────────────────────┤
│  Boundary Layer (v0.1 / v0.2 / v0.3 — preserved, demoted)     │
│    policy_os/, syscalls/, memory/, trace/, data_guard/        │
│    maintainability/, review/, prompts/, etc.                  │
├──────────────────────────────────────────────────────────────┤
│  Provider / Integration Layer (preserved)                     │
│    providers/, providers_runtime/, mcp/, integrations/,       │
│    intent/, opengod/, release/, …                             │
└──────────────────────────────────────────────────────────────┘
```

## 2. Module map

### 2.1 `loopos.loop_engine` (new, v0.4.0)

The product-facing orchestrator.

| File | Owns |
|------|------|
| `models.py` | `UserGoal`, `SuccessCriteria`, `PlanCandidate`, `BuildResult`, `TestResult`, `ReviewFinding`, `RepairPlan`, `OptimizationPlan`, `LoopIteration`, `LoopState` |
| `goal.py` | `GoalEngine` — normalizes raw goal text, generates criteria |
| `imagination.py` | `ImaginationSandbox` — `ImaginationRequest` / `CreativeCandidate` / `ImaginationResult` (no syscalls, no policy blocks) |
| `commitment.py` | `CommitmentBoundary` — `CommitmentProposal`, gates idea → action |
| `planner.py` | `LoopPlanner` — emits `PlanCandidate` per iteration |
| `builder.py` | `LoopBuilder` — emits `BuildResult` (simulated by default) |
| `tester.py` | `LoopTester` — emits `TestResult` (simulated by default) |
| `reviewer.py` | `LoopReviewer` — emits `ReviewFinding` (10 categories) |
| `repair.py` | `RepairEngine` — emits `RepairPlan` from findings |
| `optimizer.py` | `LoopOptimizer` — emits `OptimizationPlan` |
| `loop.py` | `LoopEngine` — the orchestrator |
| `events.py` | Loop-level events |
| `trace.py` | Trace integration |

### 2.2 `loopos.quality` (new, v0.4.0)

The measurement layer.

| File | Owns |
|------|------|
| `models.py` | `QualityScore`, `ConvergenceStatus`, `DeliveryCandidate` |
| `scorer.py` | `QualityScorer` — six-dimension scoring + weighted overall |
| `convergence.py` | `ConvergenceEngine` — decide continue / deliver / blocked / budget exhausted |
| `delivery.py` | `DeliveryEngine` — emit `DeliveryCandidate` with evidence |
| `evidence.py` | Evidence collection and formatting |
| `defects.py` | Defect tracking across iterations |

### 2.3 `loopos.fusion_optimizer` (new, v0.4.0)

The optimization layer, *not* the verdict layer.

| File | Owns |
|------|------|
| `models.py` | `FusionOptimizationRequest`, `FusionOptimizationResult` |
| `optimizer.py` | `FusionOptimizer` — multi-candidate next-plan recommender |
| `candidates.py` | Plan candidate comparison / ranking |
| `resolver.py` | Merge / resolve conflicting suggestions |
| `critique.py` | Critique engine for plan candidates |
| `mad_dog.py` | `MadDogReviewer` — extreme quality attacker (10 categories) |
| `verifier.py` | Evidence verification |

### 2.4 `loopos.boundary` (new, v0.4.0)

A thin compatibility / documentation layer over `policy_os` and
`syscalls`. It does **not** re-implement safety; it gives the loop
engine a single, import-stable surface.

| File | Owns |
|------|------|
| `action_boundary.py` | `ActionBoundary` — facade over PolicyEngine + SyscallRouter |
| `commitment.py` | `CommitmentGate` — validates `CommitmentProposal` |

### 2.5 `loopos.kernel` (preserved)

The Kernel Loop Engine remains the low-level execution backend. The
v0.4.0 `LoopEngine` can drive a `KernelLoopEngine` for real AIL
execution, or it can run in simulated mode.

## 3. Data flow

```text
UserGoal
  └─► GoalEngine
        └─► SuccessCriteria
              └─► LoopEngine.run()
                    ├─► LoopPlanner.plan()              → PlanCandidate
                    ├─► LoopBuilder.build()             → BuildResult
                    ├─► LoopTester.test()               → TestResult
                    ├─► LoopReviewer.review()           → [ReviewFinding]
                    ├─► RepairEngine.repair()           → RepairPlan | None
                    ├─► LoopOptimizer.optimize()        → OptimizationPlan | None
                    ├─► QualityScorer.score()           → QualityScore
                    ├─► ConvergenceEngine.decide()      → ConvergenceStatus
                    └─► DeliveryEngine.evaluate()       → DeliveryCandidate
                          (only after convergence)
```

The flow is **deterministic and bounded**. Every step produces typed
data. There are no hidden globals, no opaque prompt blobs, and no
LLM calls in the simulated path.

## 4. Boundary discipline

The v0.4.0 layer follows three boundary rules:

1. **Policy gates actions, not ideas.** The `ImaginationSandbox` and
   the `LoopPlanner` emit advisory risk labels, not policy blocks.
   Hard policy checks fire only inside `ActionBoundary` / `CommitmentGate`
   and only on real side effects (file writes, shell, network, etc.).
2. **Syscall gates side effects, not reasoning.** Reasoning, planning,
   and review are pure functions. They produce typed records, not
   `SyscallRequest` objects.
3. **Trace captures decisions, not thoughts.** Each iteration is
   traceable; each review finding carries evidence; each convergence
   decision has a rationale.

## 5. Compatibility with v0.2 / v0.3

- `KernelLoopEngine`, `PolicyEngine`, `SyscallRouter`, `Memory`,
  `Trace` — all preserved, all import-stable.
- `loopos.fusion_router` — preserved for compatibility; v0.4.0 adds
  `loopos.fusion_optimizer` on top, not in place of it.
- `loopos.core.LoopEngine` (deprecated in v0.2) — still importable
  with a DeprecationWarning for v0.4.0; slated for removal in v0.5.
- `loopos.cli.app` — preserves every v0.2 / v0.3 subcommand; adds
  `loop`, `imagine`, and `mad-dog` on top.

## 6. Non-goals for the architecture

- v0.4.0 does **not** replace the Kernel; it sits above it.
- v0.4.0 does **not** delete the Fusion Router; it adds an optimizer
  layer that can use the router as a backend.
- v0.4.0 does **not** change the AIL or AI-ISA codecs; it consumes
  them.

## 7. Related reading

- [Loop Engineering Runtime](loop-engineering-runtime.md)
- [Core Loop](core-loop.md)
- [Fusion Optimizer](fusion-optimizer.md)
- [Mad Dog Quality Attacker](mad-dog-quality-attacker.md)
- [Action Boundary](action-boundary.md)
