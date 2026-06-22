"""Tests for the Fusion Router kernel-wiring adapter."""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any

from loopos.aci.models import AgentCommandResult
from loopos.ali.models import AgentLoopSession
from loopos.fusion_router.models import (
    FusionPlan,
    FusionTaskProfile,
    FusionTrigger,
    ModelCapabilityProfile,
)
from loopos.fusion_router.router import FusionRouter
from loopos.fusion_router.runner import (
    FusionRunner,
    describe_plan_mode,
)


def _router() -> FusionRouter:
    return FusionRouter(
        profiles=[
            ModelCapabilityProfile(
                provider_id="local", model_id="local",
                reasoning_score=5, coding_score=5, review_score=5,
            ),
        ],
    )


def _plan(**overrides: object) -> FusionPlan:
    task_kwargs: dict[str, object] = dict(
        title="refactor auth", task_type="refactor",
        complexity_score=8,
    )
    task_kwargs.update(overrides)
    task = FusionTaskProfile(**task_kwargs)  # type: ignore[arg-type]
    trigger = FusionTrigger(source="user", reason="large_refactor")
    return _router().plan(task, trigger)


class _StubKernelEngine:
    """In-memory kernel engine for tests.

    Records every ``submit_agent_command`` call and returns a
    canned :class:`AgentCommandResult`. Mirrors the small
    surface of ``KernelLoopEngine.submit_agent_command`` without
    touching the kernel package.
    """

    def __init__(
        self,
        *,
        status: str = "completed",
        success: bool = True,
        reason_codes: list[str] | None = None,
    ) -> None:
        self.calls: list[AgentCommandResult] = []
        self._status = status
        self._success = success
        self._reason_codes = list(reason_codes or [])

    def submit_agent_command(
        self,
        command: Any,
        session: AgentLoopSession,
        *,
        aci_runner: Any = None,
        fsm: Any = None,
    ) -> AgentCommandResult:
        from loopos.policy_os.models import PolicyDecision

        trace_id = f"trace-{len(self.calls)}"
        result = AgentCommandResult(
            command_id=command.id,
            goal_id=command.goal_id,
            status=self._status,
            success=self._success,
            reason_codes=list(self._reason_codes),
            trace_id=trace_id,
            metadata={"trace_id": trace_id},
            policy_decision=PolicyDecision(
                allowed=self._success,
                action="allow" if self._success else "deny",
                risk="low",
                safety_level="L0",
            ),
        )
        self.calls.append(result)
        return result


class FusionRunnerDryRunTests(unittest.TestCase):
    def test_dry_run_returns_planning_only(self) -> None:

        plan = _plan()
        runner = FusionRunner(kernel_engine=_StubKernelEngine())
        result = runner.dry_run(plan)
        self.assertEqual(result.status, "planning_only")
        self.assertEqual(result.fallback_reason, "dry_run")
        self.assertEqual(result.records, [])
        self.assertEqual(result.results, [])

    def test_dry_run_persists_plan(self) -> None:
        import tempfile
        from pathlib import Path
        from loopos.fusion_router.persistence import FusionPlanStore

        with tempfile.TemporaryDirectory() as tmp:
            store = FusionPlanStore(Path(tmp) / "fusion")
            plan = _plan()
            runner = FusionRunner(store=store)
            runner.dry_run(plan)
            self.assertTrue(store.has_plan(plan.fusion_id))


class FusionRunnerNoKernelTests(unittest.TestCase):
    def test_run_without_kernel_returns_planning_only(self) -> None:
        import tempfile
        from pathlib import Path
        from loopos.fusion_router.persistence import FusionPlanStore

        with tempfile.TemporaryDirectory() as tmp:
            store = FusionPlanStore(Path(tmp) / "fusion")
            plan = _plan()
            runner = FusionRunner(kernel_engine=None, store=store)
            result = runner.run(plan)
            self.assertEqual(result.status, "planning_only")
            self.assertIn(
                "kernel_engine",
                result.fallback_reason or "",
            )

    def test_run_with_execution_disabled_returns_planning_only(self) -> None:
        import tempfile
        from pathlib import Path
        from loopos.fusion_router.persistence import FusionPlanStore

        with tempfile.TemporaryDirectory() as tmp:
            store = FusionPlanStore(Path(tmp) / "fusion")
            plan = _plan()
            engine = _StubKernelEngine()
            runner = FusionRunner(kernel_engine=engine, store=store)
            result = runner.run(plan, execution_enabled=False)
            self.assertEqual(result.status, "planning_only")
            self.assertEqual(result.fallback_reason, "execution_enabled=False")
            self.assertEqual(len(engine.calls), 0)


class FusionRunnerKernelWiringTests(unittest.TestCase):
    def test_run_dispatches_through_kernel_engine(self) -> None:
        import tempfile
        from pathlib import Path
        from loopos.fusion_router.persistence import FusionPlanStore

        with tempfile.TemporaryDirectory() as tmp:
            store = FusionPlanStore(Path(tmp) / "fusion")
            engine = _StubKernelEngine()
            plan = _plan()
            runner = FusionRunner(kernel_engine=engine, store=store)
            result = runner.run(plan)
            self.assertEqual(result.status, "accepted")
            self.assertEqual(len(engine.calls), len(plan.recommended_aci_commands))
            self.assertEqual(len(result.results), len(plan.recommended_aci_commands))

    def test_run_preserves_reason_codes_and_trace_ids(self) -> None:
        import tempfile
        from pathlib import Path
        from loopos.fusion_router.persistence import FusionPlanStore

        with tempfile.TemporaryDirectory() as tmp:
            store = FusionPlanStore(Path(tmp) / "fusion")
            engine = _StubKernelEngine(reason_codes=["audit:ok"])
            plan = _plan()
            runner = FusionRunner(kernel_engine=engine, store=store)
            result = runner.run(plan)
            self.assertIn("audit:ok", result.reason_codes)
            self.assertTrue(any(t.startswith("trace-") for t in result.trace_ids))

    def test_run_rejected_status_when_kernel_blocks(self) -> None:
        import tempfile
        from pathlib import Path
        from loopos.fusion_router.persistence import FusionPlanStore

        with tempfile.TemporaryDirectory() as tmp:
            store = FusionPlanStore(Path(tmp) / "fusion")
            engine = _StubKernelEngine(status="blocked", success=False)
            plan = _plan()
            runner = FusionRunner(kernel_engine=engine, store=store)
            result = runner.run(plan)
            self.assertEqual(result.status, "rejected")


class FusionRunnerSafetyTests(unittest.TestCase):
    def test_runner_does_not_call_live_provider(self) -> None:
        from pathlib import Path
        runner_path = Path("loopos/fusion_router/runner.py")
        assert runner_path.exists()
        with runner_path.open(encoding="utf-8") as handle:
            source = handle.read()
        for forbidden in (
            "requests.",
            "httpx.",
            "urllib.request.urlopen",
            "subprocess.run",
            "subprocess.Popen",
            "os.system",
        ):
            self.assertNotIn(
                forbidden, source,
                f"runner.py contains {forbidden!r}; "
                "FusionRunner must not call a live provider API "
                "or spawn a subprocess.",
            )

    def test_runner_does_not_import_loopos_kernel(self) -> None:
        # The runner uses a Protocol (``_KernelEngineLike``) so it
        # does not need to import KernelLoopEngine at module load
        # time. Tests inject a stub that satisfies the Protocol.
        import loopos.fusion_router.runner as runner_mod

        self.assertFalse(
            hasattr(runner_mod, "KernelLoopEngine")
            and runner_mod.KernelLoopEngine is not None,
        )
        runner_path = Path("loopos/fusion_router/runner.py")
        with runner_path.open(encoding="utf-8") as handle:
            source = handle.read()
        # The runner may mention the kernel integration in
        # docstrings but must not ``import`` it.
        self.assertNotIn("from loopos.kernel", source)
        self.assertNotIn("import loopos.kernel", source)


class FusionRunnerPreservesFieldsTests(unittest.TestCase):
    def test_describe_plan_mode_roundtrip(self) -> None:
        plan = _plan()
        description = describe_plan_mode(plan)
        self.assertEqual(description["fusion_id"], plan.fusion_id)
        self.assertEqual(description["mode"], plan.mode)
        self.assertEqual(description["fusion_score"], plan.fusion_score)
        self.assertEqual(
            description["live_provider_calls_allowed"],
            plan.live_provider_calls_allowed,
        )

    def test_run_records_ali_event_records(self) -> None:
        # The stub kernel engine does not emit ALI events; we
        # just verify that the runner's records list is populated
        # even when the stub emits nothing (so the slice math does
        # not crash). For a real kernel the records will reflect
        # the session events produced by ``consume_aci_result``.
        import tempfile
        from pathlib import Path
        from loopos.fusion_router.persistence import FusionPlanStore

        with tempfile.TemporaryDirectory() as tmp:
            store = FusionPlanStore(Path(tmp) / "fusion")
            engine = _StubKernelEngine()
            plan = _plan()
            runner = FusionRunner(kernel_engine=engine, store=store)
            result = runner.run(plan)
            # The stub produces no records; the runner must return
            # an empty list without crashing.
            self.assertIsInstance(result.records, list)
            self.assertEqual(len(result.results), len(plan.recommended_aci_commands))


if __name__ == "__main__":
    unittest.main()