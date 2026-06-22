"""Policy-binding tests for the Agent Command Interface.

These tests assert that the ACI layer is a thin wrapper over the
existing Policy OS / Syscall path:

* an allowed command carries an allow policy decision;
* a denied command carries a deny policy decision and never reaches
  a side-effecting adapter;
* a dangerous command keeps its L5 safety level through the runner;
* the runner consults Policy OS at least once for every dispatch.
"""

from __future__ import annotations

import tempfile
import unittest
from unittest import mock

from loopos.aci import (
    AgentCommand,
    AgentCommandResult,
    CommandRunner,
    RunnerConfig,
)
from loopos.policy_os.engine import PolicyEngine
from loopos.policy_os.models import PolicyDecision
from loopos.syscalls.router import create_default_syscall_router


def _make_runner(tmp: str) -> CommandRunner:
    return CommandRunner(
        policy_engine=PolicyEngine.load_default(),
        syscall_router=create_default_syscall_router(tmp, auto_approve_medium=True),
        config=RunnerConfig(workspace=tmp, run_id="run-pb"),
    )


def _low_cmd() -> AgentCommand:
    return AgentCommand(
        goal_id="g",
        purpose="p",
        kind="terminal.exec",
        command="echo hello",
    )


def _high_cmd() -> AgentCommand:
    return AgentCommand(
        goal_id="g",
        purpose="p",
        kind="terminal.exec",
        command="git reset --hard",
    )


def _blocked_cmd() -> AgentCommand:
    return AgentCommand(
        goal_id="g",
        purpose="p",
        kind="terminal.exec",
        command="rm -rf /",
    )


class PolicyBindingTests(unittest.TestCase):
    def test_low_risk_command_carries_allow_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = _make_runner(tmp).run(_low_cmd())
            self.assertTrue(result.policy_decision.allowed)
            self.assertEqual(result.status, "completed")
            self.assertTrue(result.success)

    def test_high_risk_command_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = _make_runner(tmp).run(_high_cmd())
            self.assertIn(result.status, {"blocked", "approval_required"})
            self.assertFalse(result.success)
            self.assertFalse(result.policy_decision.allowed)

    def test_dangerous_command_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = _make_runner(tmp).run(_blocked_cmd())
            self.assertEqual(result.status, "blocked")
            self.assertEqual(result.policy_decision.safety_level, "L5")

    def test_policy_engine_evaluated_for_every_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = PolicyEngine.load_default()
            router = create_default_syscall_router(tmp, auto_approve_medium=True)
            with mock.patch.object(engine, "evaluate", wraps=engine.evaluate) as spy:
                runner = CommandRunner(
                    policy_engine=engine,
                    syscall_router=router,
                    config=RunnerConfig(workspace=tmp, run_id="run-sp"),
                )
                runner.run(_low_cmd())
                self.assertTrue(spy.called)
                scope = spy.call_args[0][0]
                self.assertEqual(scope, "terminal.execute")

    def test_denied_decision_does_not_reach_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            router = create_default_syscall_router(tmp, auto_approve_medium=True)
            original = router.registry.resolve("terminal.exec").handler
            called = {"value": False}

            def spy(call):  # type: ignore[no-untyped-def]
                called["value"] = True
                return original(call)

            # Replace handler with a spy.
            from loopos.syscalls.registry import SyscallRegistry  # noqa: F401
            from loopos.syscalls.types import RegisteredSyscall  # noqa: F401

            router.registry._items["terminal.exec"] = RegisteredSyscall(
                spec=router.registry.resolve("terminal.exec").spec,
                handler=spy,  # type: ignore[arg-type]
            )
            runner = CommandRunner(
                policy_engine=PolicyEngine.load_default(),
                syscall_router=router,
                config=RunnerConfig(workspace=tmp, run_id="run-deny"),
            )
            result = runner.run(_blocked_cmd())
            self.assertEqual(result.status, "blocked")
            # Adapter handler should NOT have been called for a denied policy.
            self.assertFalse(called["value"])

    def test_aci_result_includes_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = _make_runner(tmp).run(_low_cmd())
            self.assertIsInstance(result, AgentCommandResult)
            self.assertIn(
                result.status, {"completed", "dry_run", "blocked", "approval_required", "failed"}
            )
            self.assertIsInstance(result.policy_decision, PolicyDecision)
            self.assertTrue(result.policy_decision.decision_id)
            # Observation, evaluation, progress, convergence are always present
            # (placeholders allowed when no kernel runtime is bound).
            self.assertIsNotNone(result.observation)
            self.assertIsNotNone(result.evaluation)
            self.assertIsNotNone(result.progress)
            self.assertIsNotNone(result.convergence)


class ACIStatusCoverageTests(unittest.TestCase):
    """Smoke check that the documented statuses are reachable."""

    def test_known_statuses_are_strings(self) -> None:
        from loopos.aci.models import AgentCommandStatus

        # Pydantic Literal type is a TypedDict / Literal; iterate via __args__.
        statuses = set(AgentCommandStatus.__args__)  # type: ignore[attr-defined]
        self.assertEqual(
            statuses,
            {
                "completed",
                "blocked",
                "failed",
                "approval_required",
                "dry_run",
                "unsupported",
            },
        )


if __name__ == "__main__":
    unittest.main()
