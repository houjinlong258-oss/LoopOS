# Convergence and Delivery

> The loop stops when the work is ready to deliver.
> Not when the budget runs out. Not when the LLM says "done".

The convergence and delivery layers answer the question: **is
this loop run finished, and what do we hand back to the user?**

For the scoring layer, see [Quality Engine](quality-engine.md).
For the core loop walkthrough, see [Core Loop](core-loop.md).

## 1. The four convergence states

```python
class ConvergenceStatus:
    status: Literal[
        "continue", "deliver", "blocked", "iteration_budget_exhausted"
    ]
    reason: str
    satisfied_criteria: list[str]
    unsatisfied_criteria: list[str]
    next_recommended_action: str | None
```

| Status | Meaning |
|--------|---------|
| `continue` | Keep iterating. There is repair or optimization work to do. |
| `deliver` | Stop. The work is ready. |
| `blocked` | Stop. There is a real blocker that the loop cannot resolve. |
| `iteration_budget_exhausted` | Stop. Budget is out and criteria are not met. |

## 2. The decision rules

`ConvergenceEngine.decide()` returns a `ConvergenceStatus`. The
rules in v0.4.0, in order:

1. **Required criteria gate.** If any *required* success criterion
   is unsatisfied, return `continue` (or `blocked` if the
   remaining gap is structural and the budget is exhausted).
2. **Blocking findings gate.** If any finding has
   `blocks_delivery=True` and is backed by evidence, return
   `continue` (or `blocked` if the budget is exhausted).
3. **Quality gate.** If `overall_quality >= threshold` and
   `goal_alignment >= goal_threshold`, return `deliver`.
4. **Budget gate.** If `index + 1 >= max_iterations`, return
   `iteration_budget_exhausted`.
5. Otherwise, return `continue` with `next_recommended_action`
   pointing to the next iteration's likely source (`repair` or
   `optimization`).

The default thresholds are:

```text
quality_threshold   = 0.75
goal_threshold      = 0.60
```

Both are overridable on `ConvergenceEngine(threshold=...)`.

## 3. `DeliveryCandidate`

When `ConvergenceStatus.status == "deliver"`, the loop engine
emits a `DeliveryCandidate`:

```python
class DeliveryCandidate:
    id: str
    goal_id: str
    summary: str
    evidence: list[str]
    quality_score: QualityScore
    known_limitations: list[str]
    open_risks: list[str]
    ready: bool
```

The `ready` flag is `True` only when:

- All required criteria are satisfied.
- No blocking finding is unaddressed.
- `quality_score.overall >= quality_threshold`.
- `quality_score.goal_alignment >= goal_threshold`.

If any of these fail, the candidate is still emitted (so the
user can see what happened), but `ready` is `False` and the
`known_limitations` / `open_risks` fields are populated.

## 4. The evidence requirement

The single most important invariant in v0.4.0 delivery is the
**evidence requirement**:

> A `DeliveryCandidate` with `ready=True` must carry non-empty
> `evidence` and a non-empty `summary`.

A candidate that is "ready" without evidence is impossible in
v0.4.0. The `DeliveryEngine` enforces this at construction time;
the v0.4 readiness check verifies the invariant at runtime.

## 5. The CLI surface

```bash
loopos loop deliver --json
```

The command shows:

- The original goal.
- Satisfied / unsatisfied criteria.
- The final `QualityScore`.
- The `TestResult` summary.
- The list of `ReviewFinding` items.
- `known_limitations`.
- `open_risks`.
- The `ready` flag and the rationale.

## 6. The "delivery is not termination" principle

`iteration_budget_exhausted` and `blocked` are **not** the same
as `deliver`. They both end the loop, but they do not produce a
`DeliveryCandidate` with `ready=True`. The user gets a
`LoopState` with `current_status` set to the appropriate value,
and the CLI surfaces the rationale.

This is what makes the loop engineering runtime honest: a run
that hits its budget without meeting its criteria is a *failed
run*, not a *delivered run*. The two states are kept apart.

## 7. Related reading

- [Quality Engine](quality-engine.md)
- [Core Loop](core-loop.md)
- [Loop Engineering Runtime](loop-engineering-runtime.md)
