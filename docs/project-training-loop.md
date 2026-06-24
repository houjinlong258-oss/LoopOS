# Project Training Loop

> LoopOS applies the **training loop of AI models** to project execution.
> Other agents execute tasks. LoopOS trains projects toward completion.

This document is the **canonical product thesis** for LoopOS v0.4.0.
If you only read one document about LoopOS, read this one.

## 1. The thesis in one paragraph

Training a model is iterative: define an objective, run a forward pass,
measure a loss, compute a gradient, take an optimizer step, checkpoint,
repeat. LoopOS applies the exact same shape to **project execution**:
the user gives a **project objective**, LoopOS runs a forward pass
(plan → build → test → review), measures a **project loss** (the gap
between the goal and the current state), produces an **evaluation
signal** (which findings should drive the next iteration), takes an
**optimization step** (the next plan candidate, proposed by the
**Fusion Optimizer**), **checkpoints** the loop state, and repeats
until the project **converges** (or the budget is exhausted).

## 2. The mapping, end to end

| ML training | LoopOS project training | Code surface |
|-------------|--------------------------|--------------|
| training objective | **project objective** | `UserGoal` / `ProjectObjective` |
| loss / cross-entropy | **project loss / gap** | `ProjectLoss` / `GoalGap` |
| forward pass | plan → build → test | `PlanCandidate`, `BuildResult`, `TestResult` |
| evaluator | **reviewer** + **evaluator signal** | `LoopReviewer`, `EvaluationSignal` |
| gradient signal | **findings as signals** | `ReviewFinding` → `EvaluationSignal` |
| adversarial evaluator | **Mad Dog** | `MadDogReviewer` |
| optimizer | **Fusion Optimizer** | `FusionOptimizer` |
| epoch | **iteration** | `TrainingIteration` (alias `LoopIteration`) |
| checkpoint | **project checkpoint** | `ProjectCheckpoint` |
| convergence | **delivery** | `ConvergenceReport`, `DeliveryCandidate` |
| fake convergence | **FakeConvergenceFinding** | `FakeConvergenceFinding` |

The mapping is **not decorative**. Every row in the table corresponds
to real code in `loopos.loop_engine` and `loopos.quality`. The aliases
are not just renamed — they are importable Pydantic v2 models that
the loop engine constructs and threads through the cycle.

## 3. The training loop, in code

```python
from loopos.loop_engine import (
    LoopEngine, UserGoal, SuccessCriteria,
    ProjectLoss, GoalGap, TrainingIteration,
    EvaluationSignal, OptimizationStep,
    ProjectCheckpoint, ConvergenceReport,
    FakeConvergenceFinding,
)
from loopos.quality import QualityScorer, ConvergenceEngine, DeliveryEngine

engine = LoopEngine()
state = engine.run(
    UserGoal(raw_goal="Build a provider runtime and harden it until tests pass"),
    max_iterations=8,
    convergence_decide=ConvergenceEngine().decide,
)

# Each iteration is a typed forward pass.
for it in state.iterations:
    assert isinstance(it, TrainingIteration)
    print(f"epoch {it.index}: plan={it.plan.title}, findings={len(it.review_findings)}")

# The loop emits an explicit checkpoint for replay.
checkpoint = ProjectCheckpoint.from_state(state)

# Convergence requires success criteria, not just "tests passed".
report = ConvergenceEngine().decide(state, state.iterations[-1].quality_score,
                                    state.iterations[-1].review_findings)
assert isinstance(report, ConvergenceReport)

# Fake convergence is rejected by the engine.
if report.fake_convergence:
    print("delivery blocked: fake convergence detected")
    for fc in report.fake_convergence:
        print(f"  - {fc.claim}")
```

## 4. The loss is real, not a metric

The `ProjectLoss` for an iteration is a deterministic, evidence-backed
function of:

* which success criteria are unsatisfied,
* which findings are blocking delivery,
* the `QualityScore` of the iteration,
* the trend across iterations (is the loss going down?).

The loop engine is not a benchmark. The loss is not a number pulled
out of the air. Every component of the loss traces back to a typed
record — a failed test, a missing criterion, a Mad Dog finding, an
optimizer step that didn't move the score.

```text
loss(iteration) =
    w_unsat * |unsatisfied required criteria|
  + w_block  * |evidence-backed blocking findings|
  + w_no_improve * 1 if quality did not improve vs prior iteration else 0
  + w_fake    * 1 if fake convergence detected else 0
```

The default weights are documented in
[`docs/quality-engine.md`](quality-engine.md). They are overridable
per project.

## 5. Evaluation signals, not freeform feedback

In ML, a gradient is a typed tensor with a known shape. In LoopOS, an
`EvaluationSignal` is a typed record with a known shape:

```python
class EvaluationSignal:
    id: str
    source: Literal["reviewer", "mad_dog", "optimizer", "test"]
    category: str           # the kind of signal
    severity: str           # how much it pushes the loss
    claim: str              # what it says about the iteration
    evidence: list[str]     # what backs the claim
    proposed_step: str      # what the optimizer should do next
    targets_loss_dim: str   # which loss dimension this signal affects
```

The Fusion Optimizer consumes `EvaluationSignal` objects (produced
from `ReviewFinding`s) to propose the next `OptimizationStep`. There
is no "freeform text feedback" channel — the signal is typed, the
step is typed, the result is typed.

## 6. The optimizer proposes the next iteration

The Fusion Optimizer is **not** a multi-model chat router and **not**
a verdict aggregator. It is the **optimizer** of the project training
loop.

* Given the current state, the loss, and the evaluation signals, it
  proposes the next best `OptimizationStep`.
* The optimization step is consumed by the `LoopPlanner` to produce
  the next `PlanCandidate`.
* The next iteration is the new forward pass.

The default `consensus` mode is a deterministic, offline-friendly
optimizer: it ranks candidates by signal coverage. External
multi-model fanout (e.g. OpenRouter Fusion) is **optional and
pluggable**; it accelerates the optimizer step but does not change
its role.

## 7. The adversarial evaluator prevents fake convergence

The most important thing an optimizer can do in ML is **not** overfit
to a spurious minimum. The most important thing an optimizer can do
in project training is **not** declare convergence on a spurious
signal.

`MadDogReviewer` is the **adversarial evaluator**. It attacks the
iteration result from 10 angles (see
[`docs/mad-dog-quality-attacker.md`](mad-dog-quality-attacker.md))
and raises `MadDogFinding` records. The `ConvergenceEngine` consumes
those findings to detect **fake convergence**:

* `success_criteria_passing` but `quality_gap` present → fake.
* `tests_passing` but `documentation_gap` blocking → fake.
* `quality_score` high but `goal_alignment` low → fake.
* `no_progress` (loss flat or rising across iterations) → fake.

When fake convergence is detected, the `ConvergenceReport` carries a
`FakeConvergenceFinding` and the delivery is **blocked or marked
incomplete** by `DeliveryEngine`. The loop does not silently declare
success.

## 8. Convergence is not "tests passed"

Convergence in LoopOS has **four** hard requirements:

1. All required success criteria are satisfied **and** carry
   evidence.
2. No evidence-backed blocking finding (from the base reviewer **or**
   the Mad Dog adversarial evaluator) is open.
3. The quality score is above the configured threshold **and** the
   loss has not been flat or rising for `K` consecutive iterations
   (no-progress gate).
4. No `FakeConvergenceFinding` is on the latest iteration's record.

If any of these are missing, the loop continues. The training is not
done.

## 9. Checkpoints are first-class

A `ProjectCheckpoint` is a snapshot of the full `LoopState` at the
end of an iteration: the project objective, the success criteria,
the iteration history, the loss trajectory, the evaluation signals,
the optimizer's next step, and the convergence report.

Checkpoints are **append-only** in v0.4.0; they are written to
`ProjectCheckpoint.from_state(state)` and can be replayed to resume
the loop. The Trace layer (`loopos.trace`) and the existing ALI
replay surface are the natural sinks for checkpoints in v0.4.x.

## 10. Safety is the action boundary

The training loop can produce actions: file writes, shell commands,
network calls, provider calls, release operations. The
`CommitmentBoundary` and the `ActionBoundary` (in `loopos.boundary`)
gate those actions. They are **not** the training loop; they are the
boundary that lets the training loop dispatch side effects safely.

> Safety is not the product thesis. Project training is the product
> thesis. Safety is what lets the project run, not why it runs.

## 11. Reading list

* [`docs/core-loop.md`](core-loop.md) — the phases, in detail
* [`docs/loop-engineering-runtime.md`](loop-engineering-runtime.md) —
  the original v0.4.0 framing, now updated with the training analogy
* [`docs/quality-engine.md`](quality-engine.md) — the loss / quality
  surface
* [`docs/convergence-and-delivery.md`](convergence-and-delivery.md) —
  the convergence gate, including fake convergence
* [`docs/fusion-optimizer.md`](fusion-optimizer.md) — the optimizer
* [`docs/mad-dog-quality-attacker.md`](mad-dog-quality-attacker.md) —
  the adversarial evaluator
* [`docs/action-boundary.md`](action-boundary.md) — the safety layer
