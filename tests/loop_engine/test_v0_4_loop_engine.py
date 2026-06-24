"""Tests for v0.4.0 ``loopos.loop_engine`` end-to-end behaviour.

These tests cover the nine core scenarios required by the v0.4.0 spec:
1. LoopEngine runs goal to iteration
2. LoopEngine generates success criteria
3. LoopEngine runs multiple iterations
4. Failed test creates a repair plan
5. Review finding feeds the next iteration
6. Optimization loop improves score
7. Loop stops when success criteria are met
8. Loop stops when iteration budget is exhausted
9. Delivery candidate requires evidence
"""

from __future__ import annotations

from collections.abc import Callable

from loopos.loop_engine import (
    BuildResult,
    LoopEngine,
    LoopState,
    PlanCandidate,
    RepairEngine,
    ReviewFinding,
    SuccessCriteria,
    TestResult,
)
from loopos.loop_engine.reviewer import LoopReviewer
from loopos.quality import (
    DeliveryEngine,
    QualityScore,
    QualityScorer,
)
from loopos.quality.models import ConvergenceStatus


def _converge_on_first_match(
    quality_threshold: float = 0.0,
) -> Callable[[LoopState, QualityScore | None, list[ReviewFinding]], ConvergenceStatus]:
    """Build a ``convergence_decide`` that returns ``deliver`` on the
    first iteration if the quality threshold is met, else ``continue``.
    """
    def _decide(
        state: LoopState,
        quality: QualityScore | None,
        findings: list[ReviewFinding],
    ) -> ConvergenceStatus:
        latest = state.iterations[-1]
        if quality is not None:
            q = quality
        else:
            assert latest.build_result is not None
            assert latest.test_result is not None
            q = QualityScorer().score(
                state,
                latest.build_result,
                latest.test_result,
                findings,
            )
        if q.overall >= quality_threshold:
            return ConvergenceStatus(
                status="deliver",
                reason=f"quality {q.overall} >= {quality_threshold}",
            )
        return ConvergenceStatus(status="continue", reason="below threshold")
    return _decide


class TestLoopEngineEndToEnd:
    def test_runs_goal_to_iteration(self) -> None:
        eng = LoopEngine()
        state = eng.run("Build a CLI", max_iterations=1, dry_run=True)
        assert len(state.iterations) == 1
        assert state.iterations[0].plan is not None
        assert state.iterations[0].build_result is not None
        assert state.iterations[0].test_result is not None

    def test_generates_success_criteria(self) -> None:
        eng = LoopEngine()
        state = eng.run(
            "Build a CLI with tests and documentation for the user",
            max_iterations=1,
        )
        items = state.success_criteria.items
        assert any(c.type == "test" for c in items)
        assert any(c.type == "doc" for c in items)
        assert any(c.type == "user_alignment" for c in items)

    def test_runs_multiple_iterations(self) -> None:
        eng = LoopEngine()
        state = eng.run("Build X", max_iterations=3, dry_run=True)
        assert len(state.iterations) == 3
        assert state.iterations[0].index == 1
        assert state.iterations[1].index == 2
        assert state.iterations[2].index == 3

    def test_failed_test_creates_repair_plan(self) -> None:
        # Plug in a tester that reports failures.
        from loopos.loop_engine import LoopTester

        def _failing_test(build: BuildResult, criteria: SuccessCriteria) -> TestResult:
            del build, criteria
            return TestResult(
                iteration_id="i1",
                status="failed",
                passed=1,
                failed=2,
                skipped=0,
                failures=["x is None", "y raises"],
            )

        eng = LoopEngine(tester=LoopTester(test_fn=_failing_test))
        state = eng.run("Build X", max_iterations=1)
        repair = state.iterations[0].repair_plan
        assert repair is not None
        # The repair plan must reference the findings the reviewer raised.
        assert len(repair.source_findings) >= 1
        # And the test criterion must be marked unsatisfied.
        for c in state.success_criteria.items:
            if c.type == "test":
                assert c.satisfied is False

    def test_review_finding_feeds_next_iteration(self) -> None:
        # A reviewer that always raises a user_goal_mismatch finding.
        class _AlwaysMismatch:
            def review(
                self,
                state: LoopState,
                plan: PlanCandidate,
                build: BuildResult | None,
                tests: TestResult | None,
            ) -> list[ReviewFinding]:
                del state, plan, build, tests
                return [
                    ReviewFinding(
                        category="user_goal_mismatch",
                        severity="medium",
                        claim="plan does not address goal",
                        evidence=["plan.success_criteria_refs is empty"],
                    )
                ]

        eng = LoopEngine(reviewer=_AlwaysMismatch())
        state = eng.run("Build X", max_iterations=2, dry_run=True)
        # The optimizer should produce an optimization plan in iteration 1,
        # which the planner picks up in iteration 2.
        assert state.iterations[0].optimization_plan is not None
        assert state.iterations[1].plan.source == "optimizer"

    def test_optimization_loop_improves_score(self) -> None:
        eng = LoopEngine()
        state = eng.run("Build X with tests and docs", max_iterations=3)
        scores = [i.quality_score.overall for i in state.iterations if i.quality_score]
        # Quality should not regress over iterations (deterministic, simulated).
        assert scores == sorted(scores), f"scores regressed: {scores}"

    def test_loop_stops_when_success_criteria_met(self) -> None:
        eng = LoopEngine()
        state = eng.run(
            "Build X",
            max_iterations=5,
            convergence_decide=_converge_on_first_match(quality_threshold=0.0),
        )
        # Quality in v0.4.0 simulated mode is always high enough; loop
        # should halt on the first iteration.
        assert state.current_status == "ready_to_deliver"
        assert len(state.iterations) == 1

    def test_loop_stops_when_iteration_budget_exhausted(self) -> None:
        # A convergence decider that never returns ``deliver``.
        def _never(
            state: LoopState,
            quality: QualityScore | None,
            findings: list[ReviewFinding],
        ) -> ConvergenceStatus:
            del state, quality, findings
            return ConvergenceStatus(status="continue", reason="never satisfied")

        eng = LoopEngine()
        state = eng.run("Build X", max_iterations=2, convergence_decide=_never)
        assert len(state.iterations) == 2
        # No deliver, so current_status should be initialized (caller's
        # responsibility to set after the loop).
        assert state.current_status in {"running", "initialized", "failed"}

    def test_delivery_candidate_requires_evidence(self) -> None:
        eng = LoopEngine()
        state = eng.run(
            "Build X",
            max_iterations=3,
            convergence_decide=_converge_on_first_match(quality_threshold=0.0),
        )
        cand = DeliveryEngine().evaluate(state)
        # Simulated runs always produce evidence (test passes, criteria
        # are satisfied, etc.). The candidate must therefore be ready.
        assert cand.ready is True
        assert cand.evidence  # non-empty

    def test_repair_engine_uses_actionable_findings(self) -> None:
        eng = RepairEngine()
        findings = [
            ReviewFinding(category="quality_gap", severity="high", claim="x", recommended_fix="do X"),
            ReviewFinding(category="missing_test", severity="medium", claim="y", recommended_fix="add test"),
        ]
        plan = eng.repair(findings, TestResult(iteration_id="i", status="simulated"))
        assert plan is not None
        assert len(plan.steps) == 2
        assert plan.priority == "high"  # top finding is high

    def test_reviewer_raises_finding_for_failed_test(self) -> None:
        rev = LoopReviewer()
        state = LoopEngine().run("X", max_iterations=1)  # build a state for the test
        from loopos.loop_engine.models import PlanCandidate as PC
        tests = TestResult(iteration_id="i", status="failed", passed=0, failed=1, failures=["boom"])
        plan = PC(title="p")
        findings = rev.review(state, plan, state.iterations[0].build_result, tests)
        assert any(f.category == "implementation_bug" for f in findings)
        assert any(f.blocks_delivery for f in findings)
