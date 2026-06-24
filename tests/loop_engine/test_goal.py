"""Tests for the v0.4.0 ``GoalEngine``."""

from __future__ import annotations

from loopos.loop_engine import (
    GoalEngine,
    UserGoal,
)


class TestGoalEngine:
    def test_normalize_from_string(self) -> None:
        eng = GoalEngine()
        g = eng.normalize("Build a CLI with tests and docs")
        assert isinstance(g, UserGoal)
        assert g.normalized_goal  # populated by default GoalEngine
        assert "  " not in g.normalized_goal  # collapsed whitespace

    def test_normalize_from_user_goal(self) -> None:
        eng = GoalEngine()
        g = UserGoal(raw_goal="  Build   a   CLI  ")
        g2 = eng.normalize(g)
        assert g2.normalized_goal == g2.normalized_goal.strip()

    def test_generate_criteria_for_test_goal(self) -> None:
        eng = GoalEngine()
        g = UserGoal(raw_goal="Build a CLI with tests")
        sc = eng.generate_criteria(g)
        assert any(c.type == "test" for c in sc.items)
        # test, doc, user_alignment are required by default
        for c in sc.items:
            if c.type in {"test", "user_alignment"}:
                assert c.required is True

    def test_generate_criteria_for_deliverable_goal(self) -> None:
        eng = GoalEngine()
        g = UserGoal(raw_goal="ship the CLI and release it")
        sc = eng.generate_criteria(g)
        assert any(c.type == "delivery" for c in sc.items)
        assert any(c.required for c in sc.items if c.type == "delivery")

    def test_generate_criteria_fallback(self) -> None:
        eng = GoalEngine()
        g = UserGoal(raw_goal="hello world")
        sc = eng.generate_criteria(g)
        # No keyword matched; a default functional criterion is present.
        assert any(c.type == "functional" for c in sc.items)

    def test_generate_criteria_with_extras(self) -> None:
        eng = GoalEngine()
        g = UserGoal(raw_goal="Build a CLI")
        sc = eng.generate_criteria(g, extra=[
            __import__("loopos.loop_engine.models", fromlist=["SuccessCriterion"]).SuccessCriterion(
                id="c_extra_1", description="Extra criterion",
            ),
        ])
        assert any(c.id == "c_extra_1" for c in sc.items)
