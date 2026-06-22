"""Tests for Fusion Router role assignment + provider selection."""

from __future__ import annotations

import unittest

from loopos.fusion_router.models import (
    FusionTaskProfile,
    FusionTrigger,
    ModelCapabilityProfile,
)
from loopos.fusion_router.roles import (
    assign_roles,
    capability_profile_from_provider,
    required_roles_for_mode,
    score_role_for_profile,
)


def _task(**overrides: object) -> FusionTaskProfile:
    defaults: dict[str, object] = dict(title="t", task_type="feature")
    defaults.update(overrides)
    return FusionTaskProfile(**defaults)  # type: ignore[arg-type]


def _trigger(**overrides: object) -> FusionTrigger:
    defaults: dict[str, object] = dict(source="user", reason="explicit_user_request")
    defaults.update(overrides)
    return FusionTrigger(**defaults)  # type: ignore[arg-type]


class FusionRolesForModeTests(unittest.TestCase):
    def test_single_role_set(self) -> None:
        self.assertEqual(required_roles_for_mode("single"), ("primary",))

    def test_pair_role_set(self) -> None:
        self.assertEqual(
            required_roles_for_mode("pair"), ("coder", "reviewer"),
        )

    def test_committee_role_set(self) -> None:
        self.assertEqual(
            required_roles_for_mode("committee"),
            ("planner", "coder", "reviewer"),
        )

    def test_attack_role_set(self) -> None:
        self.assertEqual(
            required_roles_for_mode("attack"),
            ("planner", "coder", "bug_hunter", "test_breaker", "judge"),
        )

    def test_mad_dog_role_set(self) -> None:
        roles = required_roles_for_mode("mad_dog")
        self.assertIn("security_guard", roles)
        self.assertIn("summarizer", roles)
        self.assertIn("reviewer", roles)
        self.assertEqual(len(roles), 10)


class FusionRolesTaskTypeTests(unittest.TestCase):
    def test_security_task_includes_security_guard(self) -> None:
        roles = required_roles_for_mode("committee", task_type="security")
        self.assertIn("security_guard", roles)

    def test_refactor_includes_architect_and_simplifier(self) -> None:
        roles = required_roles_for_mode("attack", task_type="refactor")
        self.assertIn("architect", roles)
        self.assertIn("simplifier", roles)

    def test_nasty_bug_includes_bug_hunter_and_test_breaker(self) -> None:
        roles = required_roles_for_mode("attack", task_type="bugfix")
        self.assertIn("bug_hunter", roles)
        self.assertIn("test_breaker", roles)

    def test_user_dissatisfaction_includes_reviewer_judge_summarizer(self) -> None:
        trigger = _trigger(reason="user_dissatisfaction")
        roles = required_roles_for_mode("committee", trigger=trigger)
        self.assertIn("reviewer", roles)
        self.assertIn("judge", roles)
        self.assertIn("summarizer", roles)


class FusionRoleAssignmentTests(unittest.TestCase):
    def test_provider_selection_deterministic(self) -> None:
        task = _task(task_type="bugfix", complexity_score=5, failure_count=2)
        trigger = _trigger(reason="repeated_failure")
        profiles = [
            ModelCapabilityProfile(provider_id="a", model_id="m1",
                                   reasoning_score=6, coding_score=9,
                                   debugging_score=8),
            ModelCapabilityProfile(provider_id="b", model_id="m1",
                                   reasoning_score=9, coding_score=5,
                                   debugging_score=5),
        ]
        a1 = assign_roles(task, "attack", profiles, trigger=trigger)
        a2 = assign_roles(task, "attack", profiles, trigger=trigger)
        self.assertEqual(
            [(x.role, x.provider_id) for x in a1],
            [(x.role, x.provider_id) for x in a2],
        )

    def test_provider_reuse_degrades_gracefully(self) -> None:
        task = _task(task_type="bugfix")
        profiles = [
            ModelCapabilityProfile(provider_id="only", model_id="only",
                                   reasoning_score=5, coding_score=5),
        ]
        assignments = assign_roles(task, "attack", profiles)
        # Multiple roles may share the only provider; the router
        # records ``provider_reused`` in capability_gaps so a
        # reviewer sees the degradation.
        reused = [
            a for a in assignments
            if "provider_reused" in a.capability_gaps
        ]
        self.assertGreaterEqual(len(reused), 1)

    def test_no_providers_yields_empty_provider_assignments(self) -> None:
        task = _task()
        assignments = assign_roles(task, "attack", [])
        self.assertEqual(len(assignments), 5)
        for assignment in assignments:
            self.assertEqual(assignment.provider_id, "")
            self.assertIn("no_providers_available", assignment.capability_gaps)

    def test_role_assignment_records_capability_gaps(self) -> None:
        profile = ModelCapabilityProfile(
            provider_id="weak", model_id="weak",
            reasoning_score=2, coding_score=2, review_score=2,
        )
        score, gaps = score_role_for_profile("reviewer", profile)
        self.assertGreater(len(gaps), 0)
        self.assertLess(score, 0.5)


class FusionProviderSelectionTests(unittest.TestCase):
    def test_capability_profile_from_registry_profile(self) -> None:
        # The registry profile is metadata-only. The bridge
        # derives a capability profile with conservative defaults.
        class _Caps:
            capabilities = ("tools", "json", "long_context")

        class _Profile:
            provider_id = "anthropic"
            name = "Anthropic"
            kind = "local_only"
            capability_hints = _Caps()

        derived = capability_profile_from_provider(_Profile())
        self.assertEqual(derived.provider_id, "anthropic")
        self.assertTrue(derived.supports_tools)
        self.assertTrue(derived.supports_json)
        self.assertTrue(derived.supports_long_context)
        self.assertTrue(derived.local_only)

    def test_capability_profile_handles_missing_capabilities(self) -> None:
        class _Profile:
            provider_id = "x"
            name = "X"
            kind = "remote"
            capability_hints = None

        derived = capability_profile_from_provider(_Profile())
        self.assertEqual(derived.provider_id, "x")
        self.assertFalse(derived.supports_tools)
        self.assertFalse(derived.supports_long_context)
        self.assertFalse(derived.local_only)


if __name__ == "__main__":
    unittest.main()