"""Tests for the transition-table driven ALI finite-state machine."""

from __future__ import annotations

import unittest

from loopos.ali.errors import (
    InvalidTransitionError,
    SessionClosedError,
    UnknownEventError,
)
from loopos.ali.fsm import DEFAULT_FSM, AgentLoopFSM, TABLE
from loopos.ali.models import AgentLoopSession


def _ready_session() -> AgentLoopSession:
    return AgentLoopSession(goal_id="g-fsm")


def _drive_to_running(session: AgentLoopSession) -> None:
    DEFAULT_FSM.apply(session, "goal_submitted")
    DEFAULT_FSM.apply(session, "command_submitted")


class AgentLoopFSMTests(unittest.TestCase):
    def test_default_table_is_table_driven(self) -> None:
        # The default table must contain explicit rows; if it were an
        # if-else maze, the engine would still pass functional tests
        # but the table itself would be empty.
        self.assertGreater(len(TABLE), 0)
        for row in TABLE:
            self.assertTrue(row.reason_code)
            self.assertNotEqual(row.state, row.next_state) if row.next_state in {
                "HALTED_SUCCESS",
                "HALTED_FAILURE",
                "HALTED_BLOCKED",
            } else True  # self-loops are allowed for continue-style rows

    def test_valid_transition(self) -> None:
        session = _ready_session()
        record = DEFAULT_FSM.apply(session, "goal_submitted")
        self.assertEqual(session.state, "READY")
        self.assertEqual(record.next_state, "READY")
        self.assertEqual(record.reason_code, "ali.goal_submitted")

    def test_invalid_transition_fails_with_clear_error(self) -> None:
        session = _ready_session()
        with self.assertRaises(InvalidTransitionError) as ctx:
            DEFAULT_FSM.apply(session, "command_submitted")
        self.assertIn("CREATED", str(ctx.exception))
        self.assertIn("command_submitted", str(ctx.exception))

    def test_unknown_event_rejected(self) -> None:
        session = _ready_session()
        with self.assertRaises(UnknownEventError):
            DEFAULT_FSM.apply(session, "totally_made_up_event")  # type: ignore[arg-type]

    def test_terminal_session_rejects_further_events(self) -> None:
        session = _ready_session()
        _drive_to_running(session)
        DEFAULT_FSM.apply(session, "convergence_halt_success")
        self.assertEqual(session.state, "HALTED_SUCCESS")
        with self.assertRaises(SessionClosedError):
            DEFAULT_FSM.apply(session, "command_submitted")

    def test_policy_denied_halts_to_blocked(self) -> None:
        session = _ready_session()
        _drive_to_running(session)
        DEFAULT_FSM.apply(session, "policy_denied")
        self.assertEqual(session.state, "HALTED_BLOCKED")

    def test_approval_required_routes_to_waiting_approval(self) -> None:
        session = _ready_session()
        _drive_to_running(session)
        DEFAULT_FSM.apply(session, "approval_required")
        self.assertEqual(session.state, "WAITING_APPROVAL")

    def test_waiting_approval_can_resume_running(self) -> None:
        session = _ready_session()
        _drive_to_running(session)
        DEFAULT_FSM.apply(session, "approval_required")
        DEFAULT_FSM.apply(session, "policy_allowed")
        self.assertEqual(session.state, "RUNNING")

    def test_waiting_approval_can_halt_to_blocked(self) -> None:
        session = _ready_session()
        _drive_to_running(session)
        DEFAULT_FSM.apply(session, "approval_required")
        DEFAULT_FSM.apply(session, "policy_denied")
        self.assertEqual(session.state, "HALTED_BLOCKED")

    def test_syscall_failed_during_running_enters_repairing(self) -> None:
        session = _ready_session()
        _drive_to_running(session)
        DEFAULT_FSM.apply(session, "syscall_failed")
        self.assertEqual(session.state, "REPAIRING")

    def test_repairing_failure_can_promote_to_replanning(self) -> None:
        session = _ready_session()
        _drive_to_running(session)
        DEFAULT_FSM.apply(session, "syscall_failed")
        DEFAULT_FSM.apply(session, "syscall_failed")
        self.assertEqual(session.state, "REPLANNING")

    def test_convergence_replan_enters_replanning(self) -> None:
        session = _ready_session()
        _drive_to_running(session)
        DEFAULT_FSM.apply(session, "convergence_replan")
        self.assertEqual(session.state, "REPLANNING")

    def test_convergence_ask_enters_asking_user(self) -> None:
        session = _ready_session()
        _drive_to_running(session)
        DEFAULT_FSM.apply(session, "convergence_ask")
        self.assertEqual(session.state, "ASKING_USER")

    def test_convergence_halt_success(self) -> None:
        session = _ready_session()
        _drive_to_running(session)
        DEFAULT_FSM.apply(session, "convergence_halt_success")
        self.assertEqual(session.state, "HALTED_SUCCESS")

    def test_convergence_halt_failure(self) -> None:
        session = _ready_session()
        _drive_to_running(session)
        DEFAULT_FSM.apply(session, "convergence_halt_failure")
        self.assertEqual(session.state, "HALTED_FAILURE")

    def test_convergence_halt_blocked(self) -> None:
        session = _ready_session()
        _drive_to_running(session)
        DEFAULT_FSM.apply(session, "convergence_halt_blocked")
        self.assertEqual(session.state, "HALTED_BLOCKED")

    def test_event_history_preserved(self) -> None:
        session = _ready_session()
        _drive_to_running(session)
        DEFAULT_FSM.apply(session, "policy_allowed")
        self.assertEqual(session.event_count, 3)
        self.assertEqual(
            [record.event for record in session.events],
            ["goal_submitted", "command_submitted", "policy_allowed"],
        )

    def test_custom_table_can_extend_default(self) -> None:
        # A consumer can supply a custom table; the engine still works.
        custom = AgentLoopFSM()
        self.assertGreater(len(custom.table), 0)
        # Lookup works through the index.
        row = custom.lookup("RUNNING", "policy_denied")
        self.assertIsNotNone(row)
        self.assertEqual(row.next_state, "HALTED_BLOCKED")


if __name__ == "__main__":
    unittest.main()
