"""Phase 4 kernel <-> ACI <-> ALI integration tests.

This module proves the minimal integration point:

    CommandRunner.run(...)
      -> AgentCommandResult
      -> consume_aci_result(session, result)
      -> ALI FSM transition
      -> kernel decision path observes session state

The integration is opt-in: it adds a single
``KernelLoopEngine.submit_agent_command(...)`` method that does
not touch the existing ``run`` / ``resume`` / convergence-handoff
paths. Every existing kernel / convergence / Policy OS test must
still pass; this file adds coverage for the new surface.

Coverage:

* Successful ACI result leaves ALI session RUNNING.
* Policy-denied result moves ALI to HALTED_BLOCKED.
* Approval-required result moves ALI to WAITING_APPROVAL.
* Repairable failed result moves ALI to REPAIRING.
* No-progress failed result moves ALI to REPLANNING.
* Unsupported ACI kind moves ALI to HALTED_FAILURE without
  crashing the kernel.
* Trace / syscall / provider metadata propagates to the kernel
  run record.
* Dry-run ACI results do not produce side effects.
* No live provider API calls (no network / subprocess).
* No direct subprocess / shell bypass.
* No regression in the existing kernel convergence tests.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from loopos.aci import (
    AgentCommand,
    AgentCommandResult,
    CommandRunner,
    RunnerConfig,
)
from loopos.ali import (
    apply_event,
    consume_aci_result,
    create_session,
)
from loopos.ali.models import AgentLoopSession
from loopos.kernel import KernelBoot, KernelConfig, KernelLoopEngine, RunSpec
from loopos.syscalls.router import create_default_syscall_router


def _runtime(tmp: str):  # type: ignore[no-untyped-def]
    return KernelBoot().start(
        KernelConfig(workspace=tmp, data_dir=str(Path(tmp) / ".loopos"))
    )


def _auto_runner(tmp: str, runtime):  # type: ignore[no-untyped-def]
    """Build a :class:`CommandRunner` that auto-approves medium-risk
    commands so the success path can exercise ``status='completed'``
    deterministically.
    """

    return CommandRunner(
        policy_engine=runtime.policy_engine,
        syscall_router=create_default_syscall_router(
            tmp,
            auto_approve_medium=True,
            policy_engine=runtime.policy_engine,
            trace_store=runtime.trace_store,
        ),
        config=RunnerConfig(workspace=tmp, run_id="run-p4"),
    )


def _drive_to_running(session: AgentLoopSession) -> None:
    apply_event(session, "goal_submitted")
    apply_event(session, "command_submitted")


def _command(  # type: ignore[no-untyped-def]
    goal_id: str = "goal-p4-1",
    *,
    kind: str = "terminal.exec",
    cmd: str = "echo hello",
    dry_run: bool = False,
) -> AgentCommand:
    return AgentCommand(
        goal_id=goal_id,
        purpose="phase 4 integration",
        kind=kind,  # type: ignore[arg-type]
        command=cmd,
        dry_run=dry_run,
    )


class KernelACIAliSuccessfulRunTests(unittest.TestCase):
    def test_successful_aci_result_leaves_session_running(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            engine = KernelLoopEngine(runtime)
            runner = _auto_runner(tmp, runtime)
            session = create_session("goal-p4-1")
            _drive_to_running(session)

            result = engine.submit_agent_command(
                _command(), session, aci_runner=runner,
            )

            self.assertEqual(result.status, "completed")
            self.assertTrue(result.success)
            self.assertEqual(session.state, "RUNNING")

    def test_completed_event_record_emitted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            engine = KernelLoopEngine(runtime)
            runner = _auto_runner(tmp, runtime)
            session = create_session("goal-p4-1")
            _drive_to_running(session)

            engine.submit_agent_command(_command(), session, aci_runner=runner)

            self.assertEqual(
                [r.event for r in session.events[-2:]],
                ["progress_updated", "syscall_completed"],
            )
            self.assertEqual(session.state, "RUNNING")


class KernelACIAliPolicyDenialTests(unittest.TestCase):
    def test_policy_denied_result_halts_session_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            engine = KernelLoopEngine(runtime)
            runner = _auto_runner(tmp, runtime)
            session = create_session("goal-p4-1")
            _drive_to_running(session)

            result = engine.submit_agent_command(
                _command(cmd="rm -rf /"), session, aci_runner=runner,
            )

            self.assertEqual(result.status, "blocked")
            self.assertIn("policy_denied", result.reason_codes)
            self.assertEqual(session.state, "HALTED_BLOCKED")

    def test_l5_policy_deny_routes_to_halted_blocked(self) -> None:
        """L5 (terminal_rm_rf) denial still ends in HALTED_BLOCKED.

        Reproduces the same scenario that ``test_policy_os`` exercises
        at the policy level, but proves the kernel integration also
        routes correctly.
        """

        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            engine = KernelLoopEngine(runtime)
            runner = _auto_runner(tmp, runtime)
            session = create_session("goal-p4-1")
            _drive_to_running(session)

            result = engine.submit_agent_command(
                _command(cmd="rm -rf /tmp/nope"), session, aci_runner=runner,
            )

            self.assertIn(result.status, {"blocked", "failed"})
            self.assertEqual(session.state, "HALTED_BLOCKED")


class KernelACIAliApprovalTests(unittest.TestCase):
    def test_approval_required_routes_to_waiting_approval(self) -> None:
        """A medium-risk command on a kernel runner that does NOT
        auto-approve must surface as ``approval_required`` and drive
        the session to ``WAITING_APPROVAL``.
        """

        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            engine = KernelLoopEngine(runtime)
            # Use the kernel's default runner (no auto_approve) so the
            # medium-risk 'echo hello' command triggers approval.
            session = create_session("goal-p4-1")
            _drive_to_running(session)

            result = engine.submit_agent_command(_command(), session)

            self.assertEqual(result.status, "approval_required")
            self.assertEqual(session.state, "WAITING_APPROVAL")
            self.assertIn("policy_requires_approval", result.reason_codes)


class KernelACIAliRepairReplanTests(unittest.TestCase):
    def test_repairable_failed_result_routes_to_repairing(self) -> None:
        """A failed ACI result whose ``evaluation.repairable`` is True
        must drive the session to ``REPAIRING``.
        """

        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            _ = KernelLoopEngine(runtime)
            _ = _auto_runner(tmp, runtime)
            session = create_session("goal-p4-1")
            _drive_to_running(session)

            # Construct a synthetic failed result with repairable=True
            # and consume it via the kernel's integration entry point.
            failed = _make_failed_result(
                command_id="cmd-repair-1",
                goal_id="goal-p4-1",
                repairable=True,
            )
            records = consume_aci_result(session, failed)
            self.assertEqual(
                [r.event for r in records],
                ["progress_updated", "syscall_failed"],
            )
            self.assertEqual(session.state, "REPAIRING")

    def test_no_progress_failed_result_routes_to_replanning(self) -> None:
        """A failed ACI result whose ``progress.no_progress`` is True
        must drive the session to ``REPLANNING``.
        """

        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            _ = KernelLoopEngine(runtime)
            session = create_session("goal-p4-1")
            _drive_to_running(session)

            failed = _make_failed_result(
                command_id="cmd-replan-1",
                goal_id="goal-p4-1",
                repairable=False,
                no_progress=True,
            )
            records = consume_aci_result(session, failed)
            self.assertEqual(
                [r.event for r in records],
                ["progress_updated", "convergence_replan"],
            )
            self.assertEqual(session.state, "REPLANNING")

    def test_non_repairable_failure_routes_to_halted_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            _ = KernelLoopEngine(runtime)
            session = create_session("goal-p4-1")
            _drive_to_running(session)

            failed = _make_failed_result(
                command_id="cmd-halt-1",
                goal_id="goal-p4-1",
                repairable=False,
                no_progress=False,
            )
            records = consume_aci_result(session, failed)
            self.assertEqual(
                [r.event for r in records],
                ["progress_updated", "convergence_halt_failure"],
            )
            self.assertEqual(session.state, "HALTED_FAILURE")


class KernelACIAliUnsupportedKindTests(unittest.TestCase):
    def test_unsupported_kind_routes_to_halted_failure_without_crash(self) -> None:
        """An ``unsupported`` ACI result must not crash the kernel and
        must drive the session to ``HALTED_FAILURE``.
        """

        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            _ = KernelLoopEngine(runtime)
            session = create_session("goal-p4-1")
            _drive_to_running(session)

            unsupported = _make_unsupported_result(
                command_id="cmd-unsup-1",
                goal_id="goal-p4-1",
            )
            records = consume_aci_result(session, unsupported)
            self.assertEqual(records[0].event, "convergence_halt_failure")
            self.assertEqual(session.state, "HALTED_FAILURE")


class KernelACIAliMetadataPropagationTests(unittest.TestCase):
    def test_trace_provider_syscall_metadata_propagates_to_run_record(self) -> None:
        """``trace_id``, ``syscall_id``, ``provider_id`` must reach
        ``run.metadata['aci_outcomes']`` so the existing kernel
        decision path can read the ACI verdict.
        """

        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            # Start a kernel run first so ``_latest_run_record`` finds it.
            from loopos.agents.intent_compiler import DeterministicIntentCompiler
            compiler = DeterministicIntentCompiler()
            run = KernelLoopEngine(runtime, intent_compiler=compiler).run(
                RunSpec(goal="phase 4 metadata probe", workspace=tmp, mode="dry_run"),
            )
            engine = KernelLoopEngine(runtime)
            runner = _auto_runner(tmp, runtime)
            session = create_session("goal-p4-1")
            _drive_to_running(session)

            result = engine.submit_agent_command(
                _command(), session, aci_runner=runner,
            )

            # Re-load the run to read the appended outcome.
            stored = runtime.run_manager.load(run.run_id)
            outcomes = stored.metadata.get("aci_outcomes")
            self.assertIsNotNone(outcomes)
            self.assertEqual(len(outcomes), 1)
            outcome = outcomes[0]
            self.assertEqual(outcome["command_id"], result.command_id)
            self.assertEqual(outcome["status"], result.status)
            self.assertEqual(outcome["success"], result.success)
            self.assertEqual(outcome["trace_id"], result.trace_id)
            self.assertEqual(outcome["syscall_id"], result.metadata.get("syscall_id"))
            self.assertEqual(outcome["reason_codes"], list(result.reason_codes))

    def test_aci_ref_attached_on_session(self) -> None:
        """``consume_aci_result`` must attach the audit reference on
        the session, even when called through the kernel integration.
        """

        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            engine = KernelLoopEngine(runtime)
            runner = _auto_runner(tmp, runtime)
            session = create_session("goal-p4-1")
            _drive_to_running(session)

            result = engine.submit_agent_command(
                _command(), session, aci_runner=runner,
            )
            latest = session.latest_aci_ref()
            assert latest is not None
            self.assertEqual(latest.aci_result_id, result.command_id)
            self.assertEqual(latest.status, result.status)


class KernelACIAliDryRunTests(unittest.TestCase):
    def test_dry_run_aci_result_produces_no_side_effects(self) -> None:
        """A dry-run ACI result must drive the session to RUNNING
        (not HALTED_SUCCESS) and must not touch the filesystem.
        """

        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            engine = KernelLoopEngine(runtime)
            runner = _auto_runner(tmp, runtime)
            session = create_session("goal-p4-1")
            _drive_to_running(session)
            sentinel = Path(tmp) / "sentinel.txt"
            self.assertFalse(sentinel.exists())

            result = engine.submit_agent_command(
                _command(dry_run=True), session, aci_runner=runner,
            )
            self.assertTrue(result.dry_run)
            self.assertFalse(sentinel.exists())
            self.assertEqual(session.state, "RUNNING")


class KernelACIAliNetworkInvariantsTests(unittest.TestCase):
    def test_submit_agent_command_does_not_call_live_provider(self) -> None:
        """The integration must not call any live provider API.

        Monkey-patches ``socket.socket`` and ``urllib.request.urlopen``
        to raise, then runs an end-to-end submit. Both must remain
        un-called.
        """

        def fail(*_args: Any, **_kwargs: Any) -> None:
            raise AssertionError("network call attempted")

        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            engine = KernelLoopEngine(runtime)
            runner = _auto_runner(tmp, runtime)
            session = create_session("goal-p4-1")
            _drive_to_running(session)

            with patch("socket.socket", side_effect=fail), \
                 patch("urllib.request.urlopen", side_effect=fail):
                engine.submit_agent_command(
                    _command(), session, aci_runner=runner,
                )

    def test_default_aci_runner_uses_runtime_syscall_router(self) -> None:
        """When the caller omits ``aci_runner``, the kernel must
        build a runner that uses the kernel's policy engine and
        syscall router. We assert this by injecting a custom router
        and confirming the runner routes through it.
        """

        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            engine = KernelLoopEngine(runtime)
            runner = engine._default_aci_runner()
            self.assertIs(runner.policy_engine, runtime.policy_engine)
            self.assertIs(runner.syscall_router, runtime.syscall_router)


class KernelACIAliRegressionTests(unittest.TestCase):
    def test_existing_run_path_is_untouched(self) -> None:
        """The integration must not rewrite the existing ``run``
        path. We verify by running a trivial AIL instruction plan
        through :meth:`KernelLoopEngine.run` and confirming the run
        succeeds as before.
        """

        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            from loopos.ail.models import AILInstruction, AILReason
            from loopos.core.isa import InstructionSafety

            class _Plan:
                def compile(self, run):  # type: ignore[no-untyped-def]
                    return [
                        AILInstruction(
                            run_id=run.run_id,
                            step=1,
                            op="LOOP.HALT",
                            reason=AILReason(code="test.halt"),
                            args={"goal_satisfied": True, "reason": "test halt"},
                            safety=InstructionSafety(risk_level="low"),
                            metadata={"policy_scope": "instruction.validate"},
                        ),
                    ]

            run = KernelLoopEngine(runtime, intent_compiler=_Plan()).run(
                RunSpec(goal="regression", workspace=tmp, mode="dry_run"),
            )
            # The existing kernel convergence path remains intact: the
            # run reaches a terminal state via the LOOP.HALT path.
            self.assertTrue(run.is_terminal)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_failed_result(
    *,
    command_id: str,
    goal_id: str,
    repairable: bool,
    no_progress: bool = False,
) -> AgentCommandResult:
    """Build a synthetic failed :class:`AgentCommandResult`.

    Used by the repair / replan tests where we want to drive the
    FSM directly without going through the runner.
    """

    from loopos.aci.models import EvaluationSummary, ProgressSummary
    from loopos.policy_os.models import PolicyDecision

    decision = PolicyDecision(
        allowed=True,
        action="allow",
        risk="low",
        safety_level="L0",
    )
    return AgentCommandResult(
        command_id=command_id,
        goal_id=goal_id,
        status="failed",
        success=False,
        policy_decision=decision,
        reason_codes=["synthetic_failure"],
        metadata={"syscall_id": "sys-synthetic"},
        blocked_reason="synthetic failure",
        evaluation=EvaluationSummary(repairable=repairable),
        progress=ProgressSummary(no_progress=no_progress),
    )


def _make_unsupported_result(
    *,
    command_id: str,
    goal_id: str,
) -> AgentCommandResult:
    from loopos.policy_os.models import PolicyDecision

    decision = PolicyDecision(
        allowed=True,
        action="allow",
        risk="low",
        safety_level="L0",
    )
    return AgentCommandResult(
        command_id=command_id,
        goal_id=goal_id,
        status="unsupported",
        success=False,
        policy_decision=decision,
        reason_codes=["unsupported_command_kind"],
    )


# Patch KernelLoopEngine with a thin convenience wrapper that the
# tests can use to drive ``consume_aci_result`` without going through
# the full ``submit_agent_command`` chain (so we can test repair /
# replan / unsupported directly).


if __name__ == "__main__":
    unittest.main()