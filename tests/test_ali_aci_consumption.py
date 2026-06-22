"""Tests for :func:`loopos.ali.session.consume_aci_result`.

These tests assert the Phase 3 mapping between
:class:`loopos.aci.AgentCommandResult` and the existing
:class:`loopos.ali.fsm.AgentLoopFSM` transition table.

Each test constructs a session in a known pre-state, runs the
consumer, then asserts:

* the recorded events are exactly the expected sequence,
* the final FSM state matches the expected terminal/intermediate state,
* the audit reference is attached,
* the propagated metadata (reason_codes, trace_id, provider_id,
  syscall_id, policy_decision) appears in the event payload.

The tests never touch the filesystem, the network, or subprocess.
They never invoke ``KernelLoopEngine``.
"""

from __future__ import annotations

import re
import socket as _socket
import unittest
import urllib.request as _urllib_request
from pathlib import Path
from unittest import mock


from loopos.aci import AgentCommandResult
from loopos.aci.models import (
    EvaluationSummary,
    PolicyDecisionSummary,
    ProgressSummary,
    ResolvedProvider,
    SyscallSummary,
)
from loopos.ali import (
    AgentLoopFSM,
    AgentLoopSession,
    apply_event,
    consume_aci_result,
    create_session,
)
from loopos.ali.errors import (
    InvalidTransitionError,
    SessionClosedError,
)
from loopos.policy_os.models import PolicyDecision


ALI_PKG = Path(__file__).resolve().parents[1] / "loopos" / "ali"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _allow_decision() -> PolicyDecision:
    return PolicyDecision(
        allowed=True,
        action="allow",
        reason_codes=["aci.test.allow"],
        safety_level="L0",
    )


def _deny_decision(*codes: str) -> PolicyDecision:
    return PolicyDecision(
        allowed=False,
        action="deny",
        reason_codes=list(codes) or ["policy_denied"],
        safety_level="L5",
    )


def _resolved(provider_id: str = "anthropic", source: str = "exact") -> ResolvedProvider:
    # ``ProviderResolutionSource`` is a Literal; pass the string and
    # let Pydantic validate it.
    return ResolvedProvider(
        provider_id=provider_id,
        display_name=provider_id.title(),
        kind="anthropic_messages",
        capabilities=["text", "reasoning"],
        source=source,  # type: ignore[arg-type]
    )


def _make_result(**overrides: object) -> AgentCommandResult:
    """Construct a fully-populated AgentCommandResult.

    Defaults are: ``status='completed'``, ``success=True``,
    ``dry_run=False``, ``requires_approval=False``. Pass keyword
    arguments to override any field.
    """
    base: dict[str, object] = {
        "command_id": "cmd-test",
        "goal_id": "goal-test",
        "status": "completed",
        "success": True,
        "policy_decision": _allow_decision(),
        "resolved_provider": _resolved(),
        "syscall": SyscallSummary(
            name="terminal.exec",
            syscall_id="syscall-1",
            success=True,
            dry_run=False,
            duration_ms=12,
        ),
        "observation": {
            "kind": "command_result",
            "success": True,
            "summary": "ok",
            "duration_ms": 12,
        },
        "trace_id": "trace-test",
        "dry_run": False,
        "requires_approval": False,
        "reason_codes": [],
        "messages": [],
        "metadata": {"syscall_id": "syscall-1"},
    }
    base.update(overrides)
    # Translate ``observation`` dict into the ObservationSummary model
    # if the caller passed a dict.
    obs = base.get("observation")
    if isinstance(obs, dict):
        from loopos.aci.models import ObservationSummary

        base["observation"] = ObservationSummary(**obs)
    return AgentCommandResult(**base)  # type: ignore[arg-type]


def _running_session() -> AgentLoopSession:
    """Return a session in ``RUNNING`` state, ready for ACI consumption."""

    s = create_session("goal-test")
    apply_event(s, "goal_submitted")
    apply_event(s, "command_submitted")
    return s


# ---------------------------------------------------------------------------
# Mapping tests
# ---------------------------------------------------------------------------


class CompletedResultMappingTests(unittest.TestCase):
    def test_completed_success_dry_run_false_emits_progress_then_syscall_completed(self) -> None:
        s = _running_session()
        result = _make_result(status="completed", success=True, dry_run=False)
        records = consume_aci_result(s, result)
        self.assertEqual(
            [r.event for r in records],
            ["progress_updated", "syscall_completed"],
        )
        self.assertEqual(s.state, "RUNNING")

    def test_completed_success_dry_run_true_emits_progress_only(self) -> None:
        s = _running_session()
        result = _make_result(status="completed", success=True, dry_run=True)
        records = consume_aci_result(s, result)
        self.assertEqual([r.event for r in records], ["progress_updated"])
        self.assertEqual(s.state, "RUNNING")


class DryRunResultMappingTests(unittest.TestCase):
    def test_dry_run_status_emits_progress_only(self) -> None:
        s = _running_session()
        result = _make_result(status="dry_run", success=False, dry_run=True)
        records = consume_aci_result(s, result)
        self.assertEqual([r.event for r in records], ["progress_updated"])
        self.assertEqual(s.state, "RUNNING")


class BlockedResultMappingTests(unittest.TestCase):
    def test_blocked_with_policy_denied_reason_emits_policy_denied(self) -> None:
        s = _running_session()
        result = _make_result(
            status="blocked",
            success=False,
            policy_decision=_deny_decision("policy_denied"),
            reason_codes=["policy_denied"],
            blocked_reason="policy denied",
        )
        records = consume_aci_result(s, result)
        self.assertEqual([r.event for r in records], ["policy_denied"])
        self.assertEqual(s.state, "HALTED_BLOCKED")

    def test_blocked_with_rm_rf_reason_emits_policy_denied(self) -> None:
        s = _running_session()
        result = _make_result(
            status="blocked",
            success=False,
            policy_decision=_deny_decision("terminal_rm_rf_denied"),
            reason_codes=["terminal_rm_rf_denied"],
            blocked_reason="destructive command",
        )
        records = consume_aci_result(s, result)
        self.assertEqual([r.event for r in records], ["policy_denied"])
        self.assertEqual(s.state, "HALTED_BLOCKED")

    def test_blocked_with_validation_reason_emits_halt_blocked(self) -> None:
        s = _running_session()
        result = _make_result(
            status="blocked",
            success=False,
            policy_decision=_allow_decision(),  # policy allowed; structural block
            reason_codes=["invalid_command"],
            blocked_reason="validation failed",
        )
        records = consume_aci_result(s, result)
        self.assertEqual([r.event for r in records], ["convergence_halt_blocked"])
        self.assertEqual(s.state, "HALTED_BLOCKED")


class ApprovalRequiredResultMappingTests(unittest.TestCase):
    def test_approval_required_emits_approval_required(self) -> None:
        s = _running_session()
        result = _make_result(
            status="approval_required",
            success=False,
            requires_approval=True,
            policy_decision=PolicyDecision(
                allowed=True,
                action="require_approval",
                reason_codes=["policy_requires_approval"],
                requires_approval=True,
                safety_level="L2",
            ),
            reason_codes=["policy_requires_approval"],
        )
        records = consume_aci_result(s, result)
        self.assertEqual([r.event for r in records], ["approval_required"])
        self.assertEqual(s.state, "WAITING_APPROVAL")


class FailedResultMappingTests(unittest.TestCase):
    def test_failed_repairable_emits_syscall_failed(self) -> None:
        s = _running_session()
        result = _make_result(
            status="failed",
            success=False,
            policy_decision=_allow_decision(),
            reason_codes=["syscall_failed"],
            evaluation=EvaluationSummary(
                goal_satisfied=False,
                repairable=True,
                reason_codes=["syscall_failed"],
            ),
            progress=ProgressSummary(no_progress=False),
        )
        records = consume_aci_result(s, result)
        self.assertEqual(
            [r.event for r in records],
            ["progress_updated", "syscall_failed"],
        )
        self.assertEqual(s.state, "REPAIRING")

    def test_failed_no_progress_emits_convergence_replan(self) -> None:
        s = _running_session()
        result = _make_result(
            status="failed",
            success=False,
            policy_decision=_allow_decision(),
            reason_codes=["no_progress"],
            evaluation=EvaluationSummary(
                goal_satisfied=False,
                repairable=False,
                reason_codes=["no_progress"],
            ),
            progress=ProgressSummary(no_progress=True),
        )
        records = consume_aci_result(s, result)
        self.assertEqual(
            [r.event for r in records],
            ["progress_updated", "convergence_replan"],
        )
        self.assertEqual(s.state, "REPLANNING")

    def test_failed_non_repairable_emits_convergence_halt_failure(self) -> None:
        s = _running_session()
        result = _make_result(
            status="failed",
            success=False,
            policy_decision=_allow_decision(),
            reason_codes=["hard_failure"],
            evaluation=EvaluationSummary(
                goal_satisfied=False,
                repairable=False,
                reason_codes=["hard_failure"],
            ),
            progress=ProgressSummary(no_progress=False),
        )
        records = consume_aci_result(s, result)
        self.assertEqual(
            [r.event for r in records],
            ["progress_updated", "convergence_halt_failure"],
        )
        self.assertEqual(s.state, "HALTED_FAILURE")


class UnsupportedResultMappingTests(unittest.TestCase):
    def test_unsupported_emits_convergence_halt_failure(self) -> None:
        s = _running_session()
        result = _make_result(
            status="unsupported",
            success=False,
            policy_decision=_allow_decision(),
            reason_codes=["unsupported_command_kind"],
        )
        records = consume_aci_result(s, result)
        self.assertEqual([r.event for r in records], ["convergence_halt_failure"])
        self.assertEqual(s.state, "HALTED_FAILURE")


# ---------------------------------------------------------------------------
# Audit reference + metadata propagation
# ---------------------------------------------------------------------------


class AuditReferenceAttachmentTests(unittest.TestCase):
    def test_consume_attaches_aci_reference(self) -> None:
        s = _running_session()
        result = _make_result(command_id="cmd-attach-1")
        consume_aci_result(s, result)
        latest = s.latest_aci_ref()
        self.assertIsNotNone(latest)
        assert latest is not None
        self.assertEqual(latest.aci_result_id, "cmd-attach-1")
        self.assertEqual(latest.status, "completed")
        self.assertTrue(latest.success)
        self.assertEqual(latest.metadata.get("trace_id"), "trace-test")
        self.assertEqual(latest.metadata.get("provider_id"), "anthropic")

    def test_consume_records_event_with_full_payload(self) -> None:
        s = _running_session()
        result = _make_result(
            status="blocked",
            success=False,
            policy_decision=_deny_decision("policy_denied"),
            reason_codes=["policy_denied", "aci.evidence"],
            trace_id="trace-xyz",
        )
        records = consume_aci_result(s, result)
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.event, "policy_denied")
        self.assertEqual(record.payload["command_id"], "cmd-test")
        self.assertEqual(record.payload["goal_id"], "goal-test")
        self.assertEqual(record.payload["aci_status"], "blocked")
        self.assertEqual(record.payload["reason_codes"], ["policy_denied", "aci.evidence"])
        self.assertEqual(record.payload["trace_id"], "trace-xyz")

    def test_consume_propagates_syscall_id(self) -> None:
        s = _running_session()
        result = _make_result(metadata={"syscall_id": "syscall-42"})
        records = consume_aci_result(s, result)
        # Find the syscall_completed event in the emitted sequence.
        syscall_completed = next(
            r for r in records if r.event == "syscall_completed"
        )
        self.assertEqual(syscall_completed.payload["syscall_id"], "syscall-42")

    def test_consume_propagates_provider_id_and_source(self) -> None:
        s = _running_session()
        result = _make_result(
            resolved_provider=_resolved(provider_id="openai", source="capability"),
        )
        records = consume_aci_result(s, result)
        syscall_completed = next(
            r for r in records if r.event == "syscall_completed"
        )
        self.assertEqual(syscall_completed.payload["provider_id"], "openai")
        self.assertEqual(syscall_completed.payload["provider_source"], "capability")

    def test_consume_propagates_policy_decision_summary(self) -> None:
        s = _running_session()
        decision = _allow_decision()
        result = _make_result(
            policy_decision=decision,
            policy_decision_summary=PolicyDecisionSummary(
                decision_id=decision.decision_id,
                allowed=True,
                action="allow",
                severity="info",
                risk="low",
                safety_level="L0",
                requires_approval=False,
                reason_codes=["policy_summary_test"],
            ),
        )
        records = consume_aci_result(s, result)
        syscall_completed = next(
            r for r in records if r.event == "syscall_completed"
        )
        self.assertEqual(
            syscall_completed.payload["policy_decision"]["decision_id"],
            decision.decision_id,
        )
        self.assertEqual(
            syscall_completed.payload["policy_decision"]["reason_codes"],
            ["policy_summary_test"],
        )


# ---------------------------------------------------------------------------
# State machine integration
# ---------------------------------------------------------------------------


class StateMachineIntegrationTests(unittest.TestCase):
    def test_consume_in_running_state_advances_correctly(self) -> None:
        s = _running_session()
        self.assertEqual(s.state, "RUNNING")
        consume_aci_result(s, _make_result())
        self.assertEqual(s.state, "RUNNING")

    def test_consume_in_created_state_raises_invalid_transition(self) -> None:
        s = create_session("goal-x")
        # s is in CREATED; syscall_completed is invalid from CREATED.
        with self.assertRaises(InvalidTransitionError):
            consume_aci_result(s, _make_result())

    def test_consume_in_terminal_state_raises_session_closed(self) -> None:
        s = _running_session()
        # Drive to HALTED_SUCCESS.
        apply_event(s, "convergence_halt_success")
        self.assertEqual(s.state, "HALTED_SUCCESS")
        with self.assertRaises(SessionClosedError):
            consume_aci_result(s, _make_result())

    def test_consume_in_repairing_state_emits_syscall_failed(self) -> None:
        s = _running_session()
        # Drive to REPAIRING via a failed syscall.
        consume_aci_result(
            s,
            _make_result(
                status="failed",
                success=False,
                evaluation=EvaluationSummary(repairable=True),
            ),
        )
        self.assertEqual(s.state, "REPAIRING")
        # A subsequent failing result from REPAIRING replans (the
        # transition table maps ``syscall_failed`` from REPAIRING to
        # REPLANNING).
        consume_aci_result(
            s,
            _make_result(
                status="failed",
                success=False,
                evaluation=EvaluationSummary(repairable=True),
            ),
        )
        self.assertEqual(s.state, "REPLANNING")

    def test_consume_multiple_results_produces_complete_event_log(self) -> None:
        s = _running_session()
        consume_aci_result(s, _make_result(command_id="cmd-1"))
        consume_aci_result(s, _make_result(command_id="cmd-2", status="dry_run"))
        consume_aci_result(s, _make_result(command_id="cmd-3"))
        # 2 from session boot (goal_submitted + command_submitted)
        # + 2 from cmd-1 (progress_updated + syscall_completed)
        # + 1 from cmd-2 (progress_updated)
        # + 2 from cmd-3 (progress_updated + syscall_completed)
        # = 7 events.
        self.assertEqual(len(s.events), 7)
        self.assertEqual(
            [r.event for r in s.events],
            [
                "goal_submitted",
                "command_submitted",
                "progress_updated",
                "syscall_completed",
                "progress_updated",
                "progress_updated",
                "syscall_completed",
            ],
        )


# ---------------------------------------------------------------------------
# Network / filesystem invariants
# ---------------------------------------------------------------------------


class NoKernelNoNetworkInvariantsTests(unittest.TestCase):
    def test_session_module_does_not_import_kernel(self) -> None:
        from loopos.ali import session as session_module

        text = Path(session_module.__file__).read_text(encoding="utf-8")
        no_doc = re.sub(r'"""[\s\S]*?""""', "", text)
        no_doc = re.sub(r"#[^\n]*", "", no_doc)
        self.assertNotIn("loopos.kernel", no_doc)
        self.assertNotIn("KernelLoopEngine", no_doc)

    def test_session_module_does_not_import_networking(self) -> None:
        from loopos.ali import session as session_module

        text = Path(session_module.__file__).read_text(encoding="utf-8")
        no_doc = re.sub(r'"""[\s\S]*?""""', "", text)
        no_doc = re.sub(r"#[^\n]*", "", no_doc)
        forbidden = (
            "import urllib", "from urllib",
            "import requests", "from requests",
            "import httpx", "from httpx",
            "import aiohttp", "from aiohttp",
            "import socket", "from socket",
        )
        offenders = [n for n in forbidden if n in no_doc]
        self.assertEqual(offenders, [], f"networking imports: {offenders}")

    def test_consume_does_not_call_network(self) -> None:
        calls: list[str] = []

        def _fail_socket(*_a: object, **_k: object) -> None:
            calls.append("socket.socket")

        def _fail_urlopen(*_a: object, **_k: object) -> None:
            calls.append("urllib.request.urlopen")

        with mock.patch.object(_socket, "socket", _fail_socket), \
             mock.patch.object(_urllib_request, "urlopen", _fail_urlopen):
            s = _running_session()
            consume_aci_result(s, _make_result())
        self.assertEqual(calls, [])


# ---------------------------------------------------------------------------
# Custom FSM
# ---------------------------------------------------------------------------


class CustomFSMTests(unittest.TestCase):
    def test_consume_uses_supplied_fsm(self) -> None:
        custom_fsm = AgentLoopFSM()
        s = create_session("goal-c")
        apply_event(s, "goal_submitted", fsm=custom_fsm)
        apply_event(s, "command_submitted", fsm=custom_fsm)
        records = consume_aci_result(s, _make_result(), fsm=custom_fsm)
        self.assertEqual(len(records), 2)
        self.assertEqual(s.state, "RUNNING")


if __name__ == "__main__":
    unittest.main()
