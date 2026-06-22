"""Tests for the Fusion Router scoring module."""

from __future__ import annotations

import unittest

from loopos.fusion_router.models import FusionTaskProfile, FusionTrigger
from loopos.fusion_router.scoring import (
    calculate_fusion_score,
    score_breakdown,
    select_fusion_mode,
    should_escalate,
)


def _task(**overrides: object) -> FusionTaskProfile:
    defaults: dict[str, object] = dict(title="t", task_type="feature")
    defaults.update(overrides)
    return FusionTaskProfile(**defaults)  # type: ignore[arg-type]


def _trigger(**overrides: object) -> FusionTrigger:
    defaults: dict[str, object] = dict(source="user", reason="explicit_user_request")
    defaults.update(overrides)
    return FusionTrigger(**defaults)  # type: ignore[arg-type]


class FusionScoringThresholdTests(unittest.TestCase):
    def test_low_score_stays_single(self) -> None:
        task = _task()
        trigger = _trigger(reason="low_confidence", severity="low")
        score = calculate_fusion_score(task, trigger)
        self.assertEqual(select_fusion_mode(score, trigger), "single")
        self.assertFalse(should_escalate(task, trigger))

    def test_repeated_failure_promotes_to_pair(self) -> None:
        task = _task(failure_count=3)
        trigger = _trigger(reason="repeated_failure", severity="medium")
        score = calculate_fusion_score(task, trigger)
        # failure_count * 3 = 9 * 1.1 (medium severity) ~= 10 -> pair.
        self.assertIn(select_fusion_mode(score, trigger), {"pair", "committee"})

    def test_large_refactor_promotes_to_attack(self) -> None:
        task = _task(
            task_type="refactor",
            complexity_score=10,
            affected_files=["a", "b", "c", "d", "e", "f", "g", "h"],
        )
        trigger = _trigger(reason="large_refactor", severity="high")
        score = calculate_fusion_score(task, trigger)
        self.assertIn(select_fusion_mode(score, trigger), {"attack", "mad_dog"})

    def test_release_blocker_bonus_pushes_into_mad_dog(self) -> None:
        task = _task(complexity_score=6, risk_score=4, failure_count=4)
        trigger = _trigger(reason="release_blocker", severity="critical")
        score = calculate_fusion_score(task, trigger)
        self.assertGreaterEqual(score, 35)
        self.assertEqual(select_fusion_mode(score, trigger), "mad_dog")

    def test_security_sensitive_bonus_pushes_into_attack(self) -> None:
        task = _task(complexity_score=8, risk_score=8)
        trigger = _trigger(reason="security_sensitive", severity="high")
        score = calculate_fusion_score(task, trigger)
        self.assertGreaterEqual(score, 25)
        self.assertIn(select_fusion_mode(score, trigger), {"attack", "mad_dog"})

    def test_no_progress_triggers_pair_or_higher(self) -> None:
        task = _task(no_progress_count=4)
        trigger = _trigger(reason="no_progress", severity="medium")
        self.assertTrue(should_escalate(task, trigger))


class FusionScoringExplicitOverrideTests(unittest.TestCase):
    def test_explicit_user_request_overrides_score_to_mad_dog(self) -> None:
        task = _task()
        trigger = _trigger(
            source="user",
            reason="explicit_user_request",
            requested_mode="mad_dog",
            severity="low",
        )
        score = calculate_fusion_score(task, trigger)
        self.assertEqual(score, 0)
        self.assertEqual(select_fusion_mode(score, trigger), "mad_dog")
        self.assertTrue(should_escalate(task, trigger))

    def test_explicit_user_request_pair(self) -> None:
        _ = _task()
        trigger = _trigger(
            source="user",
            reason="explicit_user_request",
            requested_mode="pair",
            severity="low",
        )
        self.assertEqual(select_fusion_mode(0, trigger), "pair")

    def test_breakdown_includes_all_components(self) -> None:
        task = _task(
            complexity_score=3,
            risk_score=4,
            failure_count=2,
            no_progress_count=1,
            user_dissatisfaction_count=1,
            affected_files=["a.py", "b.py"],
        )
        trigger = _trigger(reason="model_mismatch", severity="high")
        breakdown = score_breakdown(task, trigger)
        for key in (
            "complexity_contribution",
            "failure_contribution",
            "user_dissatisfaction_contribution",
            "risk_contribution",
            "affected_files_contribution",
            "no_progress_contribution",
            "raw_score_before_bonuses",
            "bonuses",
            "severity_multiplier",
            "fusion_score",
            "selected_mode",
            "explicit_user_request",
        ):
            self.assertIn(key, breakdown)


class FusionScoringDeterminismTests(unittest.TestCase):
    def test_same_inputs_same_score(self) -> None:
        task = _task(complexity_score=4, failure_count=2, affected_files=["x", "y"])
        trigger = _trigger(reason="repeated_failure", severity="medium")
        score_a = calculate_fusion_score(task, trigger)
        score_b = calculate_fusion_score(task, trigger)
        self.assertEqual(score_a, score_b)


if __name__ == "__main__":
    unittest.main()