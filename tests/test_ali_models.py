"""Tests for ALI state and event models."""

from __future__ import annotations

import json
import unittest
from typing import get_args

from pydantic import ValidationError

from loopos.ali.models import (
    AgentLoopEvent,
    AgentLoopSession,
    AgentLoopState,
    TERMINAL_STATES,
    TransitionRow,
)


class StateAndEventTaxonomyTests(unittest.TestCase):
    def test_required_states_present(self) -> None:
        required = {
            "CREATED",
            "READY",
            "RUNNING",
            "WAITING_APPROVAL",
            "REPAIRING",
            "REPLANNING",
            "ASKING_USER",
            "HALTED_SUCCESS",
            "HALTED_FAILURE",
            "HALTED_BLOCKED",
        }
        self.assertEqual(set(get_args(AgentLoopState)), required)

    def test_required_events_present(self) -> None:
        required = {
            "goal_submitted",
            "command_submitted",
            "policy_allowed",
            "policy_denied",
            "approval_required",
            "syscall_completed",
            "syscall_failed",
            "observation_recorded",
            "evaluation_applied",
            "progress_updated",
            "convergence_continue",
            "convergence_repair",
            "convergence_replan",
            "convergence_ask",
            "convergence_halt_success",
            "convergence_halt_failure",
            "convergence_halt_blocked",
        }
        self.assertEqual(set(get_args(AgentLoopEvent)), required)

    def test_terminal_states(self) -> None:
        self.assertEqual(
            TERMINAL_STATES,
            frozenset({"HALTED_SUCCESS", "HALTED_FAILURE", "HALTED_BLOCKED"}),
        )


class TransitionRowTests(unittest.TestCase):
    def test_transition_row_validates(self) -> None:
        row = TransitionRow(
            state="RUNNING",
            event="policy_denied",
            next_state="HALTED_BLOCKED",
            reason_code="ali.test",
        )
        self.assertEqual(row.next_state, "HALTED_BLOCKED")
        self.assertEqual(row.reason_code, "ali.test")

    def test_transition_row_rejects_unknown_state(self) -> None:
        with self.assertRaises(ValidationError):
            TransitionRow(
                state="UNKNOWN",
                event="policy_denied",
                next_state="HALTED_BLOCKED",
                reason_code="ali.test",
            )


class AgentLoopSessionTests(unittest.TestCase):
    def test_session_round_trip(self) -> None:
        session = AgentLoopSession(goal_id="g-1", metadata={"k": "v"})
        encoded = session.model_dump_json()
        decoded = AgentLoopSession.model_validate_json(encoded)
        self.assertEqual(decoded.goal_id, "g-1")
        self.assertEqual(decoded.state, "CREATED")
        self.assertEqual(decoded.metadata, {"k": "v"})

    def test_session_requires_goal_id(self) -> None:
        with self.assertRaises(ValidationError):
            AgentLoopSession(goal_id="")
        with self.assertRaises(ValidationError):
            AgentLoopSession(goal_id="   ")

    def test_session_attaches_aci_reference_without_kernel(self) -> None:
        """Sessions can reference ACI results without importing kernel internals."""
        session = AgentLoopSession(goal_id="g-2")
        session.attach_aci_result(
            aci_result_id="cmd-1",
            status="blocked",
            success=False,
            goal_id="g-2",
            blocked_reason="policy denied",
        )
        latest = session.latest_aci_ref()
        assert latest is not None
        self.assertEqual(latest.aci_result_id, "cmd-1")
        self.assertFalse(latest.success)
        self.assertTrue(latest.requires_approval is False)

    def test_session_event_cap_enforced(self) -> None:
        from loopos.ali.models import AgentLoopEventRecord

        records = [
            AgentLoopEventRecord(
                seq=i,
                event="goal_submitted",
                payload={},
                reason_code="ali.test",
                next_state="READY",
            )
            for i in range(3)
        ]
        with self.assertRaises(ValidationError):
            AgentLoopSession(
                goal_id="g-3",
                max_events=2,
                events=records,
            )

    def test_session_serialization_is_stable(self) -> None:
        # Sessions with the same goal_id share the same state shape.
        s1 = AgentLoopSession(goal_id="g-4")
        s2 = AgentLoopSession(goal_id="g-4")
        d1 = json.loads(s1.model_dump_json())
        d2 = json.loads(s2.model_dump_json())
        for key in ("goal_id", "state", "max_events", "events", "aci_refs"):
            self.assertEqual(d1[key], d2[key])


if __name__ == "__main__":
    unittest.main()
