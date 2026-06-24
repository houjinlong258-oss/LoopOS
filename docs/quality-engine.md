# Quality Engine

> Every iteration has a score. The score drives the next iteration.

The Quality Engine is the v0.4.0 measurement layer. It does not
build, test, or review — those are loop phases. It scores what
the loop has produced and emits convergence decisions based on
the score.

For the loop walkthrough, see [Core Loop](core-loop.md). For
convergence, see [Convergence and Delivery](convergence-and-delivery.md).

## 1. `QualityScore`

```python
class QualityScore:
    overall: float
    goal_alignment: float
    test_health: float
    defect_health: float
    design_health: float
    documentation_health: float
    delivery_readiness: float
    reasons: list[str]
```

All seven fields are real-valued in `[0.0, 1.0]`. The `overall`
field is a weighted sum of the other six.

## 2. The weighting

The v0.4.0 default weights are:

```text
overall = 0.30 * goal_alignment
        + 0.25 * test_health
        + 0.20 * defect_health
        + 0.10 * design_health
        + 0.05 * documentation_health
        + 0.10 * delivery_readiness
```

The weights are **explicit**, **documented**, and **overridable**
via `QualityScorer(weights=...)`. They are not learned in v0.4.0.

The intent:

- **goal_alignment** is the heaviest weight. A change that does
  not advance the user's goal is the most expensive kind of
  wasted work.
- **test_health** comes second. A green build that does not
  survive its own test suite is a false positive.
- **defect_health** third. Open review findings, especially
  blocking ones, dominate everything below them.
- **design_health**, **documentation_health**, and
  **delivery_readiness** are smaller. They matter, but they
  should not outweigh the first three.

## 3. `QualityScorer`

```python
class QualityScorer:
    def __init__(self, weights: QualityWeights | None = None): ...
    def score(
        self,
        state: LoopState,
        build: BuildResult,
        tests: TestResult,
        findings: list[ReviewFinding],
    ) -> QualityScore: ...
```

The scorer is **deterministic** for a given input. The same
`(state, build, tests, findings)` will always produce the same
`QualityScore`. There is no LLM call in the scoring path.

## 4. How each dimension is computed

The exact formula is in `loopos/quality/scorer.py`. The short
version:

- **goal_alignment** — text overlap + criterion coverage. Empty
  plans get 0.0; plans that mention every required criterion
  get 1.0; plans that mention the goal's intent get 0.5+.
- **test_health** — `passed / max(passed + failed, 1)`. A
  simulated test result with no failures scores 1.0; a
  partial result with two failures and three passes scores
  0.6.
- **defect_health** — `1.0 - 0.2 * len(high) - 0.1 * len(medium) - 0.05 * len(low)`. A clean review gets 1.0; three high-severity findings drag it to 0.4.
- **design_health** — penalised when `weak_design` or
  `regression_risk` findings are present.
- **documentation_health** — penalised when `documentation_gap`
  findings are present.
- **delivery_readiness** — penalised when `release_gap` or
  `security_risk` findings are present.

The formulas are deliberately simple. The point is not to invent
a metric; the point is to make progress visible and to give the
convergence engine a basis for the "should we keep iterating?"
decision.

## 5. What the score is used for

The score feeds three downstream consumers:

1. The `ConvergenceEngine` uses `overall` and `goal_alignment` to
   decide whether to deliver.
2. The `LoopEngine` writes the score into the `LoopIteration`
   record, so the score history is part of the loop state.
3. The CLI surfaces the score in `loop status` and `loop review`.

## 6. What the score is **not** for

- It is not a security gate. `security_risk` findings feed the
  `delivery_readiness` dimension, but a high overall score does
  not waive a critical security finding. The convergence engine
  handles that case explicitly.
- It is not a benchmark. v0.4.0 does not ship cross-project
  score comparisons; the numbers are only meaningful within a
  single loop run.
- It is not a replacement for human review. The score is
  deterministic and offline; the human review is neither.

## 7. Related reading

- [Core Loop](core-loop.md)
- [Convergence and Delivery](convergence-and-delivery.md)
- [Mad Dog Quality Attacker](mad-dog-quality-attacker.md)
- [Fusion Optimizer](fusion-optimizer.md)
