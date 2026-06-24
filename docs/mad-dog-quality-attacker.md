# Mad Dog — Adversarial Evaluator

> Mad Dog is the **adversarial evaluator** of the project training loop.
> It exists to **prevent fake convergence**.

In v0.2 and v0.3, the Mad Dog was positioned as a security
gatekeeper. That was a category error. In v0.4.0 Mad Dog is the
**adversarial evaluator** of the Project Training Loop. It attacks
the iteration from 10 angles to make sure the loop has not
"converged" on a spurious minimum.

The most important job of the Mad Dog is **not** to block work. It
is to make sure the loop never declares a project "ready" when it
isn't. The `ConvergenceEngine` consumes the Mad Dog's
`FakeConvergenceFinding` records and rejects delivery when the
adversary wins.

## 1. The 10 categories

`MadDogFinding.category` is one of:

| Category | What it attacks |
|----------|-----------------|
| `fake_completion` | Claims a thing is done when it isn't |
| `missing_test` | Code or behavior without test coverage |
| `weak_design` | A design that will not survive the next iteration |
| `implementation_bug` | A bug in the implementation itself |
| `regression_risk` | A change that will break an existing invariant |
| `quality_gap` | A quality dimension (readability, naming, test density) is below bar |
| `user_goal_mismatch` | The work is technically correct but does not satisfy the user's goal |
| `documentation_gap` | Behavior exists but is undocumented |
| `release_gap` | The change is not safe to release (migration, rollback, observability) |
| `security_risk` | A real security issue — not a hypothetical one |

## 2. What Mad Dog does not do

These anti-patterns are explicit. They are enforced by the
finding model itself and by the surrounding `MadDogReviewer`.

- Mad Dog **does not block brainstorms**. A `MadDogFinding` raised
  against a `CreativeCandidate` is recorded, but it does not stop
  the candidate from being emitted by `ImaginationSandbox`.
- Mad Dog **does not block risky ideas**. Risky ideas go to the
  `CommitmentBoundary` and are gated there, not at the Mad Dog
  layer.
- Mad Dog **does not execute anything**. It is a *reviewer*. It
  produces typed findings.
- Mad Dog **does not gate delivery on category alone**. A
  `MadDogFinding` blocks delivery only when
  `blocks_delivery=True` **and** `evidence` is non-empty.

## 3. The `MadDogFinding` model

```python
class MadDogFinding:
    id: str
    category: Literal[
        "fake_completion", "missing_test", "weak_design",
        "implementation_bug", "regression_risk", "quality_gap",
        "user_goal_mismatch", "documentation_gap", "release_gap",
        "security_risk",
    ]
    severity: Literal["info", "low", "medium", "high", "critical"]
    claim: str
    attack: str
    evidence: list[str]
    required_fix: str
    blocks_delivery: bool
```

The `evidence` field is required for delivery blocking. A
finding without evidence is **advisory**: it can raise the
priority of a repair or optimization plan, but it cannot gate
delivery on its own.

## 4. Where Mad Dog runs in the loop

```text
Plan → Build → Test
                  ↓
              Review            ← base reviewer (10 categories)
                  ↓
            Mad Dog              ← adversarial evaluator
                                    (same 10 categories, higher severity,
                                    evidence-required, can produce
                                    FakeConvergenceFinding)
                  ↓
            Evaluation signals   ← findings → typed gradient
                  ↓
            ProjectLoss          ← loss is recomputed
                  ↓
            ConvergenceReport    ← fake_convergence list populated
                  ↓
            Delivery / Continue  ← blocked when is_fake is True
```

Mad Dog does not *replace* the base `LoopReviewer`. It runs **on
top of it**. The two layers are merged into a single finding list.
The `MadDogReviewer` is allowed to escalate the severity of existing
findings, but it is not allowed to *lower* the severity of a
base-reviewer finding — that would let an attacker hide a real
issue by reclassifying it.

## 5. The "evidence gate" invariant

The single most important invariant in v0.4.0 Mad Dog is the
**evidence gate**:

> A `MadDogFinding` that sets `blocks_delivery=True` must carry
> at least one entry in `evidence`. A finding that fails the gate
> is downgraded to `blocks_delivery=False`.

This is enforced inside `MadDogReviewer.review()`. The v0.4
readiness check verifies the invariant at runtime.

## 6. CLI

```bash
# Run a Mad Dog attack against a target
loopos mad-dog attack docs/reports/v0-4-0-loop-engineering-rebuild.md --json

# Include Mad Dog in the loop review
loopos loop review --mad-dog --json
```

Both commands emit JSON. Both are safe to run in CI.

## 7. Related reading

- [Fusion Optimizer](fusion-optimizer.md) — Mad Dog runs inside the optimizer
- [Quality Engine](quality-engine.md) — Mad Dog findings feed the score
- [Convergence and Delivery](convergence-and-delivery.md) — evidence gate
