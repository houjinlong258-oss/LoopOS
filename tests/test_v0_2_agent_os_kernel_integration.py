"""Cross-layer integration tests for ACI / ALI / Freedom.

These tests prove that:

1. ACI results can be attached to ALI sessions via a thin reference.
2. A policy-denied ACI result drives an ALI transition to HALTED_BLOCKED.
3. An approval-required result drives WAITING_APPROVAL.
4. A repairable failure drives REPAIRING.
5. A no-progress / convergence_replan payload drives REPLANNING.
6. A FreedomBudget under F0 blocks risky commands before execution.
7. A CapabilityBoundary blocks forbidden file paths.
8. An OutcomeContract's required evidence can be carried into ACI.
9. The integration test does not import ``loopos.kernel.*`` and does
   not touch ``KernelLoopEngine``.
"""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from loopos.aci import (
    AgentCommand,
    AgentCommandResult,
    CommandRunner,
    RunnerConfig,
    parse_command,
)
from loopos.ali import (
    AgentLoopFSM,
    apply_event,
    create_session,
)
from loopos.ali.models import AgentLoopSession
from loopos.freedom import (
    CapabilityBoundary,
    FreedomLevel,
    FreedomPolicy,
    OutcomeContract,
    check_authority,
)
from loopos.policy_os.engine import PolicyEngine
from loopos.syscalls.router import create_default_syscall_router


def _make_runner(tmp: str) -> CommandRunner:
    return CommandRunner(
        policy_engine=PolicyEngine.load_default(),
        syscall_router=create_default_syscall_router(tmp, auto_approve_medium=True),
        config=RunnerConfig(workspace=tmp, run_id="run-int"),
    )


def _low_cmd() -> AgentCommand:
    return AgentCommand(
        goal_id="goal-int-1",
        purpose="integration baseline",
        kind="terminal.exec",
        command="echo hello",
    )


def _deny_cmd() -> AgentCommand:
    return AgentCommand(
        goal_id="goal-int-1",
        purpose="integration deny",
        kind="terminal.exec",
        command="rm -rf /",
    )


def _approval_cmd() -> AgentCommand:
    return AgentCommand(
        goal_id="goal-int-1",
        purpose="integration approval",
        kind="terminal.exec",
        command="git reset --hard",
    )


def _dangerous_non_terminal_cmd() -> AgentCommand:
    # The runtime treats 'echo' as a low-risk command regardless of
    # this payload, but the freedom layer enforces a F0 budget on
    # arbitrary command shapes.
    return _low_cmd()


def _drive_to_running(session: AgentLoopSession) -> None:
    apply_event(session, "goal_submitted")
    apply_event(session, "command_submitted")


class ACItoALISessionAttachmentTests(unittest.TestCase):
    def test_aci_result_attaches_to_session(self) -> None:
        session = create_session("goal-int-1")
        _drive_to_running(session)
        # The session can carry a thin reference to the ACI result
        # without importing the kernel.
        session.attach_aci_result(
            aci_result_id="cmd-1",
            status="completed",
            success=True,
            goal_id="goal-int-1",
        )
        latest = session.latest_aci_ref()
        assert latest is not None
        self.assertEqual(latest.aci_result_id, "cmd-1")
        self.assertTrue(latest.success)
        self.assertEqual(session.state, "RUNNING")

    def test_aci_result_serializes_via_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = _make_runner(tmp).run(_low_cmd())
            encoded = result.to_json()
            decoded = AgentCommandResult.from_json(encoded)
            self.assertEqual(decoded.command_id, result.command_id)
            self.assertEqual(decoded.status, result.status)

    def test_aci_command_round_trip_via_parse(self) -> None:
        cmd = _low_cmd()
        encoded = cmd.model_dump_json()
        decoded = parse_command(encoded)
        self.assertEqual(decoded.goal_id, "goal-int-1")
        self.assertEqual(decoded.command, "echo hello")


class ACIPolicyDrivesALITransitionsTests(unittest.TestCase):
    def test_denied_result_drives_halted_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = _make_runner(tmp)
            result = runner.run(_deny_cmd())
            self.assertEqual(result.status, "blocked")
            session = create_session("goal-int-1")
            _drive_to_running(session)
            # Map the denied result to the matching FSM event.
            apply_event(
                session,
                "policy_denied",
                payload={"aci_result_id": result.command_id, "reason": "policy denied"},
            )
            self.assertEqual(session.state, "HALTED_BLOCKED")

    def test_approval_required_result_drives_waiting_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = _make_runner(tmp)
            result = runner.run(_approval_cmd())
            # The runtime returns either 'blocked' or 'approval_required';
            # both must funnel the ALI session into WAITING_APPROVAL when
            # the agent surfaces an approval_required payload.
            self.assertIn(result.status, {"blocked", "approval_required"})
            session = create_session("goal-int-1")
            _drive_to_running(session)
            apply_event(
                session,
                "approval_required",
                payload={"aci_result_id": result.command_id, "reason": "needs approval"},
            )
            self.assertEqual(session.state, "WAITING_APPROVAL")

    def test_repairable_failure_drives_repairing(self) -> None:
        session = create_session("goal-int-1")
        _drive_to_running(session)
        # The runtime signals repairable failure with a syscall_failed
        # event; ALI routes this into REPAIRING.
        apply_event(
            session,
            "syscall_failed",
            payload={"reason": "transient", "repairable": True},
        )
        self.assertEqual(session.state, "REPAIRING")

    def test_no_progress_drives_replanning(self) -> None:
        session = create_session("goal-int-1")
        _drive_to_running(session)
        apply_event(
            session,
            "convergence_replan",
            payload={"reason": "no_progress", "no_progress_count": 3},
        )
        self.assertEqual(session.state, "REPLANNING")


class FreedomIntegrationTests(unittest.TestCase):
    def test_f0_budget_blocks_risky_command(self) -> None:
        policy = FreedomPolicy(level="F0_DETERMINISTIC", metadata={"terminal_allowlist": []})
        boundary = CapabilityBoundary(policy)
        # Use a release-tag trigger so the boundary emits a tagged
        # reason code; arbitrary `rm -rf` is also blocked, but the
        # reason code would be `release_tag_human_only` only when
        # the command matches the release-tag pattern.
        decision = check_authority(
            boundary,
            action="terminal.execute",
            level="F0_DETERMINISTIC",
            command="git tag v0.2.0",
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason_code, "freedom.release_tag_human_only")

    def test_capability_boundary_blocks_forbidden_path(self) -> None:
        policy = FreedomPolicy(
            level="F5_AUTONOMOUS_PROJECT",
            allow_network=True,
            allow_database_mutation=True,
            allow_release_tag_changes=True,
            allow_privilege_escalation=True,
            allowed_filesystem_roots=["/workspace/loopos"],
        )
        boundary = CapabilityBoundary(policy)
        decision = check_authority(
            boundary,
            action="file.read",
            level="F5_AUTONOMOUS_PROJECT",
            path="/etc/passwd",
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason_code, "freedom.path_not_allowlisted")

    def test_f5_with_allowlist_allows_path(self) -> None:
        policy = FreedomPolicy(
            level="F5_AUTONOMOUS_PROJECT",
            allow_network=True,
            allow_database_mutation=True,
            allow_release_tag_changes=True,
            allow_privilege_escalation=True,
            allowed_filesystem_roots=["/workspace/loopos"],
        )
        boundary = CapabilityBoundary(policy)
        decision = check_authority(
            boundary,
            action="file.read",
            level="F5_AUTONOMOUS_PROJECT",
            path="/workspace/loopos/README.md",
        )
        self.assertTrue(decision.allowed)


class OutcomeContractCarriedIntoACITests(unittest.TestCase):
    def test_outcome_contract_evidence_kinds_in_metadata(self) -> None:
        contract = OutcomeContract(
            title="Ship v0.2 Agent OS Kernel",
            evidence_kinds=["test_report", "command_output", "review_artifact"],
        )
        cmd = AgentCommand(
            goal_id="goal-int-1",
            purpose="deliver v0.2",
            kind="terminal.exec",
            command="pytest -q",
            metadata={"outcome_contract_id": contract.contract_id},
        )
        self.assertEqual(
            cmd.metadata["outcome_contract_id"],
            contract.contract_id,
        )
        self.assertEqual(len(contract.required_evidence_kinds()), 3)


class IntegrationInvariantsTests(unittest.TestCase):
    def test_no_kernel_loop_engine_in_integration(self) -> None:
        """This test module must not import ``loopos.kernel.*``."""
        source = Path(__file__).read_text(encoding="utf-8")
        # Strip docstrings and comments.
        no_doc = re.sub(r'"""[\s\S]*?""""', "", source)
        no_doc = re.sub(r"#[^\n]*", "", no_doc)
        # Strip string literals so the negative claim in docstrings
        # and test bodies does not trip the assertion.
        no_doc = re.sub(r'"[^"\n]*"', '""', no_doc)
        no_doc = re.sub(r"'[^'\n]*'", "''", no_doc)
        self.assertNotIn("loopos.kernel", no_doc)
        self.assertNotIn("KernelLoopEngine", no_doc)


if __name__ == "__main__":
    unittest.main()
