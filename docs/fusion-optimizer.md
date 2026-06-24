# Fusion Optimizer

> Fusion in v0.4.0 is the **optimizer** of the Project Training Loop.
> It consumes the loss + evaluation signals and produces the
> **next best iteration**.

The `loopos.fusion_optimizer` package is the v0.4.0 product layer
for multi-candidate next-plan optimization. It is **not** a
verdict-aggregator and it is **not** a chat-orchestrator — both of
those are anti-patterns that v0.4.0 explicitly leaves behind.

In the project-training-loop framing, Fusion is the **optimizer**.
It takes the current loss (`ProjectLoss`) and the typed evaluation
signals (`EvaluationSignal`) and produces the next
`OptimizationStep`. The `LoopPlanner` consumes the optimization
step to produce the next `PlanCandidate`, and the loop engine
turns that into the next forward pass.

For the legacy verdict / escalation surface, see
[Fusion Router](fusion-router.md). The router is preserved for
compatibility; the optimizer is what new code should use.

## 1. The v0.4.0 mental model

```text
Old (v0.2 / v0.3):
  Ask N models. Aggregate. Emit a verdict. Block or pass.

New (v0.4.0):
  Read the loss + evaluation signals (the gradient).
  Generate N plan candidates (parameter proposals).
  Critique each (gradient inspection).
  Verify each against findings and tests (validation).
  Attack the strongest one with Mad Dog (adversarial check).
  Resolve the survivors into a single recommended next plan
    (the optimizer step).
  Hand the plan to LoopEngine (the next forward pass).
```

The output of the optimizer is **a plan**, not a verdict. The
plan is consumed by the loop engine on the next iteration. The
loop engine, in turn, runs the build/test/review cycle and feeds
back into the optimizer for the iteration after that.

## 2. Inputs and outputs

```python
class FusionOptimizationRequest:
    goal: UserGoal
    success_criteria: SuccessCriteria
    current_state: LoopState
    previous_iteration: LoopIteration | None
    candidates: list[PlanCandidate]
    mode: Literal["creative", "repair", "optimize", "mad_dog", "consensus"]

class FusionOptimizationResult:
    recommended_next_plan: PlanCandidate
    alternatives: list[PlanCandidate]
    review_findings: list[ReviewFinding]
    repair_plan: RepairPlan | None
    optimization_plan: OptimizationPlan | None
    rationale: str
    disagreements: list[str]
    confidence: float
```

## 3. The five roles

`FusionOptimizer` orchestrates five roles. Each role is a
pluggable component:

| Role | Owns |
|------|------|
| `planner` | generate `PlanCandidate` objects |
| `critic` | produce `ReviewFinding` against a candidate |
| `verifier` | cross-check candidate against prior findings and tests |
| `mad_dog` | extreme quality attack across 10 categories |
| `resolver` | merge surviving candidates into a single next plan |

In v0.4.0 each role is implemented as a deterministic,
offline-only function. External multi-model fanout (e.g. OpenRouter
Fusion) is **optional and pluggable**; the default backend works
without any external API.

## 4. Modes

| Mode | What the optimizer does |
|------|-------------------------|
| `creative` | generate fresh candidates; ignore prior findings |
| `repair` | prioritize candidates that address the prior iteration's findings |
| `optimize` | prioritize candidates that improve the lowest-quality dimension |
| `mad_dog` | run a full Mad Dog attack against the current best candidate |
| `consensus` | weight candidates by structural similarity (cheap, no LLM) |

The `consensus` mode is the v0.4.0 default — it is the most
honest mode for a simulated, LLM-less build: it does not pretend
to know which candidate the user would have picked.

## 5. The non-execution invariant

`FusionOptimizer.optimize()` is a **pure function** in v0.4.0.
It does not:

- dispatch a syscall
- write a file
- make a network call
- call a paid provider
- update durable memory

It produces a `FusionOptimizationResult` and stops. The
`LoopEngine` is the only thing that dispatches.

## 6. CLI

```bash
loopos fusion optimize --json
loopos mad-dog attack <target> --json
```

Both commands emit JSON. Both are safe to run in CI.

## 7. Migration from `fusion_router`

The legacy `loopos.fusion_router` package is preserved. The
mapping is:

| `fusion_router` concept | `fusion_optimizer` equivalent |
|--------------------------|--------------------------------|
| `FusionTrigger` (verdict trigger) | `FusionOptimizationRequest.mode` |
| `FusionPlan` (verdict plan) | `FusionOptimizationResult.recommended_next_plan` |
| `MadDogVerdict` (security verdict) | `MadDogFinding` (10-category quality attack) |
| CLI: `fusion-router plan` | CLI: `fusion optimize` (different output schema) |
| CLI: `mad-dog attack` | CLI: `mad-dog attack` (now 10 categories) |

New code should import from `loopos.fusion_optimizer`. Legacy
imports from `loopos.fusion_router` keep working.

## 8. Related reading

- [Mad Dog Quality Attacker](mad-dog-quality-attacker.md)
- [Loop Engineering Runtime](loop-engineering-runtime.md)
- [Core Loop](core-loop.md)
- [Fusion Router (legacy)](fusion-router.md)
