"""Tests for Fusion Router provider selection (separate file for clarity)."""

from __future__ import annotations

import unittest

from loopos.fusion_router.models import (
    FusionTaskProfile,
    ModelCapabilityProfile,
)
from loopos.fusion_router.roles import assign_roles


class FusionProviderRoleMatchingTests(unittest.TestCase):
    def test_coder_prefers_high_coding_score(self) -> None:
        task = FusionTaskProfile(title="t", task_type="feature")
        profiles = [
            ModelCapabilityProfile(
                provider_id="bad", model_id="m",
                coding_score=3, reasoning_score=8, review_score=3,
            ),
            ModelCapabilityProfile(
                provider_id="good", model_id="m",
                coding_score=9, reasoning_score=5, review_score=5,
            ),
        ]
        assignments = assign_roles(task, "pair", profiles)
        coder = next(a for a in assignments if a.role == "coder")
        self.assertEqual(coder.provider_id, "good")

    def test_reviewer_prefers_high_review_score(self) -> None:
        task = FusionTaskProfile(title="t", task_type="feature")
        profiles = [
            ModelCapabilityProfile(
                provider_id="bad", model_id="m",
                coding_score=9, reasoning_score=5, review_score=2,
            ),
            ModelCapabilityProfile(
                provider_id="good", model_id="m",
                coding_score=5, reasoning_score=5, review_score=9,
            ),
        ]
        assignments = assign_roles(task, "pair", profiles)
        reviewer = next(a for a in assignments if a.role == "reviewer")
        self.assertEqual(reviewer.provider_id, "good")

    def test_provider_selection_is_deterministic_across_runs(self) -> None:
        task = FusionTaskProfile(
            title="t", task_type="bugfix", failure_count=3,
        )
        profiles = [
            ModelCapabilityProfile(
                provider_id="alpha", model_id="m",
                reasoning_score=8, coding_score=7, debugging_score=9,
            ),
            ModelCapabilityProfile(
                provider_id="beta", model_id="m",
                reasoning_score=7, coding_score=8, debugging_score=8,
            ),
            ModelCapabilityProfile(
                provider_id="gamma", model_id="m",
                reasoning_score=8, coding_score=6, debugging_score=7,
            ),
        ]
        a1 = assign_roles(task, "attack", profiles)
        a2 = assign_roles(task, "attack", profiles)
        self.assertEqual(
            [(a.role, a.provider_id) for a in a1],
            [(a.role, a.provider_id) for a in a2],
        )


if __name__ == "__main__":
    unittest.main()