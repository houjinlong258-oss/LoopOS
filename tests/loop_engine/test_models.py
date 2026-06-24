"""Tests for v0.4.0 loop_engine Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from loopos.loop_engine.models import (
    BuildResult,
    LoopIteration,
    LoopState,
    OptimizationPlan,
    PlanCandidate,
    RepairPlan,
    REVIEW_CATEGORIES,
    ReviewFinding,
    SuccessCriteria,
    SuccessCriterion,
    TestResult,
    UserGoal,
)


class TestUserGoal:
    def test_user_goal_minimal(self) -> None:
        g = UserGoal(raw_goal="Build a CLI")
        assert g.id.startswith("goal_")
        assert g.raw_goal == "Build a CLI"
        assert g.normalized_goal == ""
        assert g.constraints == []

    def test_user_goal_normalized(self) -> None:
        g = UserGoal(raw_goal="Build   a   CLI   with   tests").normalized()
        assert " " in g.normalized_goal
        assert g.normalized_goal.strip() == g.normalized_goal

    def test_user_goal_rejects_extra(self) -> None:
        with pytest.raises(ValidationError):
            UserGoal(raw_goal="x", unknown_field=1)  # type: ignore[call-arg]

    def test_user_goal_keeps_existing_normalized(self) -> None:
        g = UserGoal(raw_goal="x", normalized_goal="already normalized")
        # normalize() returns self when normalized_goal is set
        assert g.normalized().normalized_goal == "already normalized"


class TestSuccessCriteria:
    def test_required_unsatisfied(self) -> None:
        sc = SuccessCriteria(items=[
            SuccessCriterion(id="c1", description="a", required=True, satisfied=False),
            SuccessCriterion(id="c2", description="b", required=True, satisfied=True),
            SuccessCriterion(id="c3", description="c", required=False, satisfied=False),
        ])
        unsat = sc.required_unsatisfied()
        assert len(unsat) == 1
        assert unsat[0].id == "c1"

    def test_mark_satisfied(self) -> None:
        sc = SuccessCriteria(items=[
            SuccessCriterion(id="c1", description="a", required=True),
        ])
        sc.mark_satisfied("c1", evidence=["ev1", "ev2"])
        assert sc.items[0].satisfied is True
        assert "ev1" in sc.items[0].evidence
        assert "ev2" in sc.items[0].evidence

    def test_default_thresholds(self) -> None:
        sc = SuccessCriteria()
        assert sc.minimum_quality_score == 0.75
        assert sc.items == []


class TestBuildAndTest:
    def test_build_result_default_simulated(self) -> None:
        br = BuildResult(iteration_id="i1", plan_id="p1")
        assert br.status == "simulated"
        assert br.errors == []

    def test_test_result_count_invariant(self) -> None:
        tr = TestResult(iteration_id="i1", status="simulated", passed=3, failed=1, skipped=0)
        assert tr.passed == 3
        assert tr.failed == 1

    def test_test_status_literal(self) -> None:
        with pytest.raises(ValidationError):
            TestResult(iteration_id="i1", status="unknown")  # type: ignore[arg-type]


class TestReviewFinding:
    def test_all_10_categories_accepted(self) -> None:
        for cat in REVIEW_CATEGORIES:
            f = ReviewFinding(category=cat, claim="x")
            assert f.category == cat

    def test_invalid_category_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ReviewFinding(category="not_a_category", claim="x")  # type: ignore[arg-type]

    def test_severity_literal(self) -> None:
        with pytest.raises(ValidationError):
            ReviewFinding(category="quality_gap", severity="super_high", claim="x")  # type: ignore[arg-type]


class TestRepairAndOptimization:
    def test_repair_plan_priority(self) -> None:
        rp = RepairPlan(source_findings=["f1"], steps=["fix"], priority="high")
        assert rp.priority == "high"

    def test_optimization_plan_required_fields(self) -> None:
        op = OptimizationPlan(target="doc", reason="missing")
        assert op.target == "doc"
        assert op.reason == "missing"
        assert op.steps == []


class TestPlanCandidate:
    def test_plan_source_literal(self) -> None:
        with pytest.raises(ValidationError):
            PlanCandidate(title="x", source="unknown")  # type: ignore[arg-type]

    def test_plan_default_source(self) -> None:
        p = PlanCandidate(title="x")
        assert p.source == "planner"


class TestLoopState:
    def test_loop_state_minimal(self) -> None:
        g = UserGoal(raw_goal="x")
        s = LoopState(goal=g)
        assert s.max_iterations == 3
        assert s.current_status == "initialized"
        assert s.iterations == []
        assert s.latest_iteration() is None

    def test_loop_state_with_iteration(self) -> None:
        g = UserGoal(raw_goal="x")
        s = LoopState(goal=g)
        s.iterations.append(LoopIteration(index=1, goal_id=g.id, plan=PlanCandidate(title="p")))
        latest = s.latest_iteration()
        assert latest is not None
        assert latest.index == 1


class TestLoopIteration:
    def test_iteration_required_plan(self) -> None:
        with pytest.raises(ValidationError):
            LoopIteration(index=1, goal_id="g")  # type: ignore[call-arg]
