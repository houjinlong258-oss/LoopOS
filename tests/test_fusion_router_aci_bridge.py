"""Tests for Fusion Router ACI bridge (recommended commands)."""

from __future__ import annotations

import unittest

from loopos.fusion_router.models import (
    FusionTaskProfile,
    FusionTrigger,
    ModelCapabilityProfile,
)
from loopos.fusion_router.router import FusionRouter


def _router() -> FusionRouter:
    profile = ModelCapabilityProfile(
        provider_id="local", model_id="local",
        reasoning_score=5, coding_score=5, review_score=5,
    )
    return FusionRouter(profiles=[profile])


def _task(**overrides: object) -> FusionTaskProfile:
    defaults: dict[str, object] = dict(title="t", task_type="feature")
    defaults.update(overrides)
    return FusionTaskProfile(**defaults)  # type: ignore[arg-type]


def _trigger(**overrides: object) -> FusionTrigger:
    defaults: dict[str, object] = dict(source="user", reason="explicit_user_request")
    defaults.update(overrides)
    return FusionTrigger(**defaults)  # type: ignore[arg-type]


class FusionACIBridgeTests(unittest.TestCase):
    def test_single_plan_has_one_recommended_command(self) -> None:
        plan = _router().plan(_task(), _trigger())
        self.assertEqual(len(plan.recommended_aci_commands), 1)
        cmd = plan.recommended_aci_commands[0]
        self.assertEqual(cmd["execution_owner"], "aci")
        self.assertTrue(cmd["dry_run"])

    def test_mad_dog_plan_has_full_command_set(self) -> None:
        task = _task(task_type="bugfix", complexity_score=8, failure_count=5)
        trigger = _trigger(reason="explicit_user_request", requested_mode="mad_dog")
        plan = _router().plan(task, trigger)
        self.assertEqual(plan.mode, "mad_dog")
        self.assertGreaterEqual(len(plan.recommended_aci_commands), 10)

    def test_recommended_commands_are_dry_run(self) -> None:
        plan = _router().plan(_task(), _trigger())
        for command in plan.recommended_aci_commands:
            self.assertTrue(command["dry_run"])

    def test_execution_owner_is_aci(self) -> None:
        plan = _router().plan(_task(), _trigger())
        for command in plan.recommended_aci_commands:
            self.assertEqual(command["execution_owner"], "aci")

    def test_router_does_not_execute_shell_or_subprocess(self) -> None:
        import loopos.fusion_router.router as router_mod
        import loopos.fusion_router.cli as cli_mod
        for module in (router_mod, cli_mod):
            module_path = module.__file__
            assert module_path is not None
            with open(module_path, encoding="utf-8") as handle:
                source = handle.read()
            for forbidden in ("subprocess.run", "subprocess.Popen", "os.system"):
                self.assertNotIn(forbidden, source,
                                 f"{module.__name__} imports / uses {forbidden}")
            # The router must not import live provider transport.
            self.assertNotIn("requests.", source)
            self.assertNotIn("httpx.", source)
            self.assertNotIn("urllib.request.urlopen", source)

    def test_router_does_not_import_loopos_kernel(self) -> None:
        import loopos.fusion_router as pkg
        import loopos.fusion_router.router as router_mod
        import loopos.fusion_router.cli as cli_mod
        for module in (pkg, router_mod, cli_mod):
            self.assertFalse(
                hasattr(module, "KernelLoopEngine")
                and module.KernelLoopEngine is not None,
                f"{module.__name__} exposes KernelLoopEngine",
            )

    def test_live_provider_calls_disallowed_by_default(self) -> None:
        plan = _router().plan(_task(), _trigger())
        self.assertFalse(plan.live_provider_calls_allowed)


class FusionPolicyBoundaryTests(unittest.TestCase):
    def test_router_recommends_only_planning_no_execution(self) -> None:
        plan = _router().plan(_task(), _trigger())
        self.assertFalse(plan.live_provider_calls_allowed)
        for command in plan.recommended_aci_commands:
            self.assertEqual(command["execution_owner"], "aci")
            self.assertTrue(command["dry_run"])


if __name__ == "__main__":
    unittest.main()