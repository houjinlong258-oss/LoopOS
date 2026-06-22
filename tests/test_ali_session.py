"""Tests for :class:`AgentLoopSession` lifecycle and ACI references."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from loopos.ali import (
    AgentLoopFSM,
    SessionConfig,
    apply_event,
    create_session,
)
from loopos.ali.errors import (
    InvalidTransitionError,
    SessionClosedError,
    UnknownEventError,
)
from loopos.ali.models import AgentLoopSession


class SessionLifecycleTests(unittest.TestCase):
    def test_create_session_initial_state(self) -> None:
        s = create_session("goal-1")
        self.assertEqual(s.state, "CREATED")
        self.assertEqual(s.goal_id, "goal-1")
        self.assertEqual(s.event_count, 0)
        self.assertFalse(s.is_terminal)

    def test_create_session_respects_config(self) -> None:
        s = create_session("goal-2", config=SessionConfig(max_events=8))
        self.assertEqual(s.max_events, 8)

    def test_apply_event_through_helper(self) -> None:
        s = create_session("goal-3")
        record = apply_event(s, "goal_submitted")
        self.assertEqual(s.state, "READY")
        self.assertEqual(record.event, "goal_submitted")

    def test_apply_event_uses_passed_fsm(self) -> None:
        s = create_session("goal-4")
        fsm = AgentLoopFSM()
        apply_event(s, "goal_submitted", fsm=fsm)
        self.assertEqual(s.state, "READY")

    def test_session_serialize_deserialize(self) -> None:
        s = create_session("goal-5")
        apply_event(s, "goal_submitted")
        apply_event(s, "command_submitted")
        payload = json.loads(s.model_dump_json())
        rebuilt = AgentLoopSession.model_validate(payload)
        self.assertEqual(rebuilt.state, "RUNNING")
        self.assertEqual(rebuilt.event_count, 2)
        self.assertEqual(
            [record.event for record in rebuilt.events],
            ["goal_submitted", "command_submitted"],
        )

    def test_session_can_persist_to_disk_and_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.json"
            s = create_session("goal-6")
            apply_event(s, "goal_submitted")
            apply_event(s, "command_submitted")
            path.write_text(s.model_dump_json(), encoding="utf-8")
            loaded = AgentLoopSession.model_validate_json(path.read_text(encoding="utf-8"))
            self.assertEqual(loaded.state, "RUNNING")
            self.assertEqual(loaded.goal_id, "goal-6")

    def test_session_no_side_effects(self) -> None:
        """Creating a session and applying events must not touch the FS or network."""
        s = create_session("goal-7")
        with (
            mock.patch("pathlib.Path.write_text") as w,
            mock.patch("pathlib.Path.read_text") as r,
            mock.patch("urllib.request.urlopen") as u,
        ):
            apply_event(s, "goal_submitted")
            apply_event(s, "command_submitted")
            self.assertFalse(w.called)
            self.assertFalse(r.called)
            self.assertFalse(u.called)

    def test_session_can_reference_aci_result_without_kernel(self) -> None:
        s = create_session("goal-8")
        s.attach_aci_result(
            aci_result_id="cmd-7",
            status="completed",
            success=True,
            goal_id="goal-8",
        )
        latest = s.latest_aci_ref()
        self.assertIsNotNone(latest)
        assert latest is not None  # mypy
        self.assertEqual(latest.aci_result_id, "cmd-7")
        self.assertEqual(latest.status, "completed")
        # Source code must not import loopos.kernel.*
        import loopos.ali.session as session_module

        source = Path(session_module.__file__).read_text(encoding="utf-8")
        import re

        no_doc = re.sub(r'"""[\s\S]*?""""', "", source)
        no_doc = re.sub(r"#[^\n]*", "", no_doc)
        self.assertNotIn("loopos.kernel", no_doc)
        self.assertNotIn("KernelLoopEngine", no_doc)


class SessionErrorPathTests(unittest.TestCase):
    def test_invalid_transition_propagates(self) -> None:
        s = create_session("goal-err-1")
        with self.assertRaises(InvalidTransitionError):
            apply_event(s, "command_submitted")

    def test_unknown_event_propagates(self) -> None:
        """An event that is not part of the ALI taxonomy is rejected."""
        s = create_session("goal-err-2")
        with self.assertRaises(UnknownEventError):
            apply_event(s, "totally_unknown_event")  # type: ignore[arg-type]

    def test_invalid_transition_is_not_unknown(self) -> None:
        s = create_session("goal-err-2b")
        with self.assertRaises(InvalidTransitionError):
            apply_event(s, "policy_denied")  # CREATED -> policy_denied is invalid

    def test_terminal_session_rejects_events(self) -> None:
        s = create_session("goal-err-3")
        apply_event(s, "goal_submitted")
        apply_event(s, "command_submitted")
        apply_event(s, "convergence_halt_success")
        with self.assertRaises(SessionClosedError):
            apply_event(s, "command_submitted")


class SessionMaxEventsTests(unittest.TestCase):
    def test_max_events_enforced(self) -> None:
        s = create_session("goal-cap", config=SessionConfig(max_events=2))
        apply_event(s, "goal_submitted")
        apply_event(s, "command_submitted")
        # The model validator runs on direct construction; we use it
        # to confirm the cap is honored.
        with self.assertRaises(Exception):
            # Construct a session whose events exceed the cap.
            from loopos.ali.models import AgentLoopEventRecord

            AgentLoopSession(
                goal_id="goal-cap",
                max_events=2,
                events=[
                    AgentLoopEventRecord(
                        seq=i,
                        event="goal_submitted",
                        payload={},
                        reason_code="ali.test",
                        next_state="READY",
                    )
                    for i in range(3)
                ],
            )


if __name__ == "__main__":
    unittest.main()
