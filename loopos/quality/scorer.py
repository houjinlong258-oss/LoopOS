"""Quality scoring: deterministic, offline, pluggable.

The v0.4.0 scorer uses a simple weighted formula on six dimensions.
The exact formulas are:

* ``goal_alignment``    = 1.0 if plan references all required criteria,
                          0.5 if references the goal text only,
                          0.0 otherwise.
* ``test_health``       = passed / max(passed + failed, 1).
* ``defect_health``     = 1.0 - 0.2 * high - 0.1 * medium - 0.05 * low
                          (clamped to [0, 1]).
* ``design_health``     = penalised for ``weak_design`` /
                          ``regression_risk`` findings.
* ``documentation_health`` = penalised for ``documentation_gap``.
* ``delivery_readiness``   = penalised for ``release_gap`` /
                              ``security_risk``.

The formulas are deliberately simple. The point is not to invent a
metric; the point is to make progress visible and to give the
``ConvergenceEngine`` a basis for the "should we keep iterating?"
decision.
"""

from __future__ import annotations

from typing import Callable

from loopos.loop_engine.models import (
    BuildResult,
    LoopState,
    ReviewFinding,
    TestResult,
)
from loopos.quality.models import QualityScore, QualityWeights


_DEFAULT_WEIGHTS = QualityWeights()


class QualityScorer:
    """Score a single iteration."""

    def __init__(
        self,
        weights: QualityWeights | None = None,
        score_fn: Callable[
            [LoopState, BuildResult, TestResult, list[ReviewFinding], QualityWeights],
            QualityScore
        ] | None = None,
    ) -> None:
        self._weights = weights or _DEFAULT_WEIGHTS
        self._score_fn = score_fn

    def score(
        self,
        state: LoopState,
        build: BuildResult,
        tests: TestResult,
        findings: list[ReviewFinding],
    ) -> QualityScore:
        if self._score_fn is not None:
            return self._score_fn(state, build, tests, findings, self._weights)
        return self._default(state, build, tests, findings)

    def _default(
        self,
        state: LoopState,
        build: BuildResult,
        tests: TestResult,
        findings: list[ReviewFinding],
    ) -> QualityScore:
        goal_alignment = _goal_alignment(state)
        test_health = _test_health(tests)
        defect_health = _defect_health(findings)
        design_health = _category_penalty(findings, {"weak_design", "regression_risk"}, 0.20)
        documentation_health = _category_penalty(findings, {"documentation_gap"}, 0.10)
        delivery_readiness = _category_penalty(
            findings, {"release_gap", "security_risk"}, 0.20,
        )

        w = self._weights
        overall = (
            w.goal_alignment * goal_alignment
            + w.test_health * test_health
            + w.defect_health * defect_health
            + w.design_health * design_health
            + w.documentation_health * documentation_health
            + w.delivery_readiness * delivery_readiness
        )
        reasons = _build_reasons(
            goal_alignment, test_health, defect_health,
            design_health, documentation_health, delivery_readiness, findings,
        )
        return QualityScore(
            overall=round(overall, 4),
            goal_alignment=round(goal_alignment, 4),
            test_health=round(test_health, 4),
            defect_health=round(defect_health, 4),
            design_health=round(design_health, 4),
            documentation_health=round(documentation_health, 4),
            delivery_readiness=round(delivery_readiness, 4),
            reasons=reasons,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _goal_alignment(state: LoopState) -> float:
    latest = state.latest_iteration()
    plan = latest.plan if latest is not None else None
    if plan is None:
        return 0.0
    required = [c for c in state.success_criteria.items if c.required]
    if not required:
        return 0.5
    refs = set(plan.success_criteria_refs)
    matched = sum(1 for c in required if c.id in refs)
    if matched == len(required):
        return 1.0
    if matched > 0:
        return 0.5 + 0.5 * (matched / len(required))
    return 0.5 if plan.rationale else 0.0


def _test_health(tests: TestResult) -> float:
    total = tests.passed + tests.failed
    if total == 0:
        # No tests means we cannot claim test_health is high.
        return 0.5 if tests.status == "simulated" else 0.0
    return tests.passed / total


def _defect_health(findings: list[ReviewFinding]) -> float:
    penalty = 0.0
    for f in findings:
        if f.severity == "critical":
            penalty += 0.30
        elif f.severity == "high":
            penalty += 0.20
        elif f.severity == "medium":
            penalty += 0.10
        elif f.severity == "low":
            penalty += 0.05
    return max(0.0, min(1.0, 1.0 - penalty))


def _category_penalty(
    findings: list[ReviewFinding], categories: set[str], per_finding: float,
) -> float:
    matching = sum(1 for f in findings if f.category in categories)
    return max(0.0, min(1.0, 1.0 - matching * per_finding))


def _build_reasons(
    goal_alignment: float,
    test_health: float,
    defect_health: float,
    design_health: float,
    documentation_health: float,
    delivery_readiness: float,
    findings: list[ReviewFinding],
) -> list[str]:
    reasons: list[str] = []
    if goal_alignment < 0.5:
        reasons.append("Plan does not reference all required success criteria.")
    if test_health < 0.5:
        reasons.append("Test health is below threshold.")
    if defect_health < 0.5:
        reasons.append(f"{len(findings)} review finding(s) present.")
    if design_health < 0.5:
        reasons.append("Design or regression risks present.")
    if documentation_health < 0.5:
        reasons.append("Documentation gap present.")
    if delivery_readiness < 0.5:
        reasons.append("Delivery / security risks present.")
    return reasons


__all__ = ["QualityScorer"]
