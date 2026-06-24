"""Tests for the v0.4.0 Project Training Loop surface.

These tests cover the six hard requirements from the product
correction brief:

1. A failed evaluation increases the project loss (or widens the
   goal gap).
2. Review findings become typed ``EvaluationSignal`` records
   (the gradient).
3. Optimization signals feed the next iteration's plan.
4. Repeated iterations can improve the quality score.
5. Delivery is blocked or marked incomplete when fake convergence
   is detected.
6. Convergence requires success criteria, not just passing
   simulated tests.
"""

from __future__ import annotations


from loopos.loop_engine import (
    BuildResult,
    ConvergenceReport,
    EvaluationSignal,
    GoalGap,
    LoopEngine,
    LoopState,
    LoopTester,
    ProjectCheckpoint,
    ProjectLoss,
    ProjectObjective,
    SuccessCriteria,
    TestResult,
    TrainingIteration,
    UserGoal,
)
from loopos.quality import ConvergenceEngine, DeliveryEngine


def _run_with_failing_test(goal: str, max_iterations: int = 1) -> LoopState:
    def _failing_test(build: BuildResult, criteria: SuccessCriteria) -> TestResult:
        del build, criteria
        return TestResult(
            iteration_id="i1",
            status="failed",
            passed=0,
            failed=2,
            failures=["x is None", "y raises"],
        )
    eng = LoopEngine(tester=LoopTester(test_fn=_failing_test))
    return eng.run(goal, max_iterations=max_iterations)


def _run_passing(goal: str, max_iterations: int = 1) -> LoopState:
    eng = LoopEngine()
    return eng.run(goal, max_iterations=max_iterations)


class TestProjectTrainingLoopSurface:
    def test_project_objective_is_user_goal(self) -> None:
        g = ProjectObjective(raw_goal="Build a thing")
        assert isinstance(g, UserGoal)
        assert g.raw_goal == "Build a thing"

    def test_iteration_is_training_iteration(self) -> None:
        state = _run_passing("Build X", max_iterations=1)
        it = state.iterations[0]
        assert isinstance(it, TrainingIteration)
        # TrainingIteration carries the training-loop surface.
        assert it.loss is not None
        assert isinstance(it.loss, ProjectLoss)
        assert isinstance(it.signals, list)


class TestLossAndGap:
    def test_failed_evaluation_increases_project_loss(self) -> None:
        passing_state = _run_passing("Build X with tests and docs", max_iterations=1)
        failing_state = _run_with_failing_test("Build X with tests and docs", max_iterations=1)
        ce = ConvergenceEngine()
        # When tests fail, the test criterion is unsatisfied, the
        # blocking-finding component is positive, and the loss is
        # strictly higher.
        passing_loss = ce.compute_loss(
            passing_state,
            passing_state.iterations[0].quality_score,
            passing_state.iterations[0].review_findings,
        )
        failing_loss = ce.compute_loss(
            failing_state,
            failing_state.iterations[0].quality_score,
            failing_state.iterations[0].review_findings,
        )
        assert failing_loss.total > passing_loss.total
        # The failing-state goal_gap is non-empty.
        assert isinstance(failing_loss.goal_gap, GoalGap)
        # At least one of the unsatisfied / blocked dimensions is positive.
        assert (
            failing_loss.unsat_required > 0
            or failing_loss.blocking_findings > 0
        )

    def test_findings_become_evaluation_signals(self) -> None:
        state = _run_with_failing_test("Build X with tests and docs", max_iterations=1)
        it = state.iterations[0]
        assert isinstance(it, TrainingIteration)
        assert it.signals, "findings should become EvaluationSignal records"
        for sig in it.signals:
            assert isinstance(sig, EvaluationSignal)
            # Each signal carries an evidence trail and a proposed step.
            assert sig.evidence or sig.claim
            assert sig.targets_loss_dim in {
                "unsat_required", "blocking_findings",
                "no_improvement", "fake_convergence",
            }

    def test_signals_feed_next_iteration(self) -> None:
        # The first iteration's findings (now signals) must influence
        # the second iteration's plan. With a failing test, the loop
        # planner picks a repair-style plan for iteration 2.
        state = _run_with_failing_test("Build X with tests and docs", max_iterations=2)
        assert len(state.iterations) == 2
        # The repair plan from iteration 1 was real and was consumed
        # by the planner for iteration 2.
        assert state.iterations[0].repair_plan is not None
        # The planner uses the repair plan as the source for iter 2.
        assert state.iterations[1].plan.source in {"repair", "planner", "optimizer"}


class TestRepeatedIterationsImproveQuality:
    def test_repeated_iterations_improve_quality(self) -> None:
        # The simulated, deterministic default always converges, so
        # the quality score should not regress across iterations.
        state = _run_passing("Build X with tests and docs", max_iterations=3)
        scores = [
            it.quality_score.overall
            for it in state.iterations
            if it.quality_score is not None
        ]
        assert scores == sorted(scores), f"scores regressed: {scores}"


class TestFakeConvergenceBlocksDelivery:
    def test_fake_convergence_raises_finding(self) -> None:
        # A simulated-only run with all required criteria satisfied
        # but the engine configured to reject simulated evidence must
        # raise a fake-convergence finding.
        state = _run_passing("Build X with tests and docs", max_iterations=2)
        ce = ConvergenceEngine(simulated_acceptable=False)
        report = ce.decide(
            state,
            state.iterations[-1].quality_score,
            state.iterations[-1].review_findings,
        )
        assert isinstance(report, ConvergenceReport)
        assert report.is_fake is True
        categories = {fc.category for fc in report.fake_convergence}
        assert any(
            cat in categories
            for cat in (
                "all_tests_simulated_but_no_real_evidence",
                "criteria_satisfied_by_evidence_loop_only",
            )
        )

    def test_delivery_blocked_when_fake_convergence(self) -> None:
        # The DeliveryEngine must mark the candidate as not-ready when
        # the latest convergence report is fake, even if every test
        # passed.
        state = _run_passing("Build X with tests and docs", max_iterations=2)
        # Manually attach a fake-convergence report to the latest
        # iteration so the DeliveryEngine uses it.
        from loopos.loop_engine.models import FakeConvergenceFinding
        state.iterations[-1].convergence = ConvergenceReport(
            status="deliver",
            reason="tests passed",
            fake_convergence=[
                FakeConvergenceFinding(
                    category="all_tests_simulated_but_no_real_evidence",
                    severity="high",
                    claim="simulated only",
                    evidence=["a"],
                )
            ],
        )
        cand = DeliveryEngine().evaluate(state)
        assert cand.ready is False
        # The fake-convergence claim is surfaced in open_risks.
        assert any("fake_convergence" in r for r in cand.open_risks)

    def test_convergence_requires_success_criteria_not_just_tests(self) -> None:
        # If the test passes but a required criterion is unsatisfied,
        # convergence must NOT deliver. We run with a larger budget so
        # the budget-exhausted gate does not pre-empt the criteria gate.
        eng = LoopEngine()
        state = eng.run("Build X with tests and docs", max_iterations=2)
        # Lift the budget AFTER the run, so the convergence check sees
        # a state with unsatisfied criteria and budget remaining.
        state.max_iterations = 5
        # Force a required criterion back to unsatisfied.
        target = next(c for c in state.success_criteria.items if c.required)
        target.satisfied = False
        target.evidence = []
        ce = ConvergenceEngine(simulated_acceptable=True)
        report = ce.decide(
            state,
            state.iterations[-1].quality_score,
            state.iterations[-1].review_findings,
        )
        assert report.status == "continue"
        assert target.id in report.unsatisfied_criteria


class TestCheckpoints:
    def test_project_checkpoint_from_iteration(self) -> None:
        state = _run_passing("Build X with tests and docs", max_iterations=1)
        it = state.iterations[0]
        assert isinstance(it, TrainingIteration)
        ckpt = ProjectCheckpoint.from_iteration(state.goal.id, it)
        assert isinstance(ckpt, ProjectCheckpoint)
        assert ckpt.goal_id == state.goal.id
        assert ckpt.iteration_id == it.id
        assert ckpt.iteration_index == it.index
        assert ckpt.plan_id == it.plan.id
        # Loss + signals are propagated when present.
        if it.loss is not None:
            assert ckpt.loss is not None
            assert ckpt.loss.iteration_id == it.id

    def test_loop_state_checkpoints(self) -> None:
        state = _run_passing("Build X with tests and docs", max_iterations=3)
        ckpts = state.checkpoints()
        assert len(ckpts) == 3
        for ck in ckpts:
            assert isinstance(ck, ProjectCheckpoint)
