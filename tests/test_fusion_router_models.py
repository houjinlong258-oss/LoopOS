"""Tests for the Fusion Router typed models."""

from __future__ import annotations

import unittest

from loopos.fusion_router.models import (
    FUSION_MODES,
    FUSION_ROLES,
    FUSION_TRIGGER_REASONS,
    FusionPlan,
    FusionRoleAssignment,
    FusionTaskProfile,
    FusionTrigger,
    FusionVerdict,
    ModelCapabilityProfile,
)


def _plan(**overrides: object) -> FusionPlan:
    """Build a deterministic minimal :class:`FusionPlan`."""

    trigger = FusionTrigger(source="user", reason="explicit_user_request")
    task = FusionTaskProfile(title="t", task_type="feature")
    defaults: dict[str, object] = dict(
        mode="single",
        trigger=trigger,
        task_profile=task,
        fusion_score=0,
        assignments=[],
    )
    defaults.update(overrides)
    return FusionPlan(**defaults)  # type: ignore[arg-type]


class FusionModelsRoundtripTests(unittest.TestCase):
    def test_plan_roundtrip(self) -> None:
        plan = _plan()
        encoded = plan.model_dump_json()
        decoded = FusionPlan.model_validate_json(encoded)
        self.assertEqual(decoded, plan)

    def test_trigger_roundtrip(self) -> None:
        trigger = FusionTrigger(
            source="kernel",
            reason="repeated_failure",
            severity="high",
            evidence={"run_id": "run-1"},
        )
        encoded = trigger.model_dump_json()
        decoded = FusionTrigger.model_validate_json(encoded)
        self.assertEqual(decoded, trigger)
        self.assertEqual(decoded.evidence, {"run_id": "run-1"})

    def test_role_assignment_roundtrip(self) -> None:
        assignment = FusionRoleAssignment(
            role="coder",
            provider_id="local",
            model_id="m",
            capability_score=0.7,
            reason="best",
        )
        encoded = assignment.model_dump_json()
        decoded = FusionRoleAssignment.model_validate_json(encoded)
        self.assertEqual(decoded, assignment)

    def test_verdict_roundtrip(self) -> None:
        verdict = FusionVerdict(
            fusion_id="f-1",
            status="accepted",
            confidence=0.9,
        )
        decoded = FusionVerdict.model_validate_json(verdict.model_dump_json())
        self.assertEqual(decoded, verdict)

    def test_capability_profile_roundtrip(self) -> None:
        profile = ModelCapabilityProfile(
            provider_id="p",
            model_id="m",
            reasoning_score=7,
            coding_score=8,
        )
        decoded = ModelCapabilityProfile.model_validate_json(profile.model_dump_json())
        self.assertEqual(decoded, profile)


class FusionModelsExtraFieldsTests(unittest.TestCase):
    def test_extra_fields_rejected_on_trigger(self) -> None:
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            FusionTrigger(
                source="user",
                reason="explicit_user_request",
                not_a_field=True,  # type: ignore[call-arg]
            )

    def test_extra_fields_rejected_on_task_profile(self) -> None:
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            FusionTaskProfile(
                title="t",
                task_type="feature",
                unknown_field=1,  # type: ignore[call-arg]
            )

    def test_extra_fields_rejected_on_capability_profile(self) -> None:
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            ModelCapabilityProfile(
                provider_id="p",
                model_id="m",
                unknown=1,  # type: ignore[call-arg]
            )

    def test_score_bounds_enforced(self) -> None:
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            ModelCapabilityProfile(
                provider_id="p", model_id="m", reasoning_score=99,
            )

    def test_unknown_mode_rejected(self) -> None:
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            _plan(mode="ultra")  # type: ignore[arg-type]

    def test_unknown_reason_rejected(self) -> None:
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            FusionTrigger(
                source="user",
                reason="because-i-said-so",  # type: ignore[arg-type]
            )


class FusionModelsTaxonomyTests(unittest.TestCase):
    def test_mode_taxonomy_complete(self) -> None:
        # The taxonomy strings are part of the wire contract; any
        # change is a breaking change.
        self.assertEqual(
            set(FUSION_MODES),
            {"single", "pair", "committee", "attack", "mad_dog"},
        )

    def test_role_taxonomy_complete(self) -> None:
        self.assertEqual(
            set(FUSION_ROLES),
            {
                "primary",
                "planner",
                "architect",
                "coder",
                "bug_hunter",
                "test_breaker",
                "reviewer",
                "security_guard",
                "simplifier",
                "judge",
                "summarizer",
            },
        )

    def test_trigger_reason_taxonomy_complete(self) -> None:
        self.assertEqual(
            set(FUSION_TRIGGER_REASONS),
            {
                "explicit_user_request",
                "repeated_failure",
                "no_progress",
                "user_dissatisfaction",
                "high_complexity",
                "large_refactor",
                "nasty_bug",
                "low_confidence",
                "high_risk",
                "release_blocker",
                "security_sensitive",
                "test_flake_or_hidden_failure",
                "model_mismatch",
            },
        )


if __name__ == "__main__":
    unittest.main()