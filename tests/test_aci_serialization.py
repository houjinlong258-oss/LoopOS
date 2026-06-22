"""Tests for :mod:`loopos.aci.serialization` wire-format helpers."""

from __future__ import annotations

import unittest

from loopos.aci import AgentCommand, AgentCommandResult
from loopos.aci.serialization import (
    command_to_wire_dict,
    deserialize_command,
    deserialize_result,
    result_to_wire_dict,
    serialize_command_payload,
    serialize_result_payload,
)
from loopos.policy_os.models import PolicyDecision


def _decision(allowed: bool = True) -> PolicyDecision:
    return PolicyDecision(
        allowed=allowed,
        action="allow" if allowed else "deny",
        reason_codes=["aci.serde_test"],
    )


class CommandSerializationTests(unittest.TestCase):
    def test_serialize_command_payload_is_stable(self) -> None:
        cmd = AgentCommand(
            goal_id="g",
            purpose="p",
            kind="terminal.exec",
            command="echo hi",
        )
        a = serialize_command_payload(cmd)
        b = serialize_command_payload(cmd)
        self.assertEqual(a, b)

    def test_serialize_excludes_none_fields(self) -> None:
        cmd = AgentCommand(
            goal_id="g",
            purpose="p",
            kind="terminal.exec",
            command="echo hi",
        )
        wire = command_to_wire_dict(cmd)
        # Optional fields that default to None MUST be omitted from the
        # wire payload. (``intent`` defaults to ``""`` so it stays in
        # the payload by design -- the agent is allowed to send an
        # explicit empty intent.)
        self.assertNotIn("cwd", wire)
        self.assertNotIn("provider_hint", wire)
        self.assertNotIn("session_id", wire)
        self.assertNotIn("outcome_contract_id", wire)
        self.assertNotIn("risk_hint", wire)
        self.assertNotIn("timeout_seconds", wire)

    def test_deserialize_command_round_trip(self) -> None:
        cmd = AgentCommand(
            goal_id="g",
            purpose="p",
            kind="file.read",
            command="README.md",
        )
        wire = command_to_wire_dict(cmd)
        decoded = deserialize_command(wire)
        self.assertEqual(decoded, cmd)

    def test_deserialize_command_from_string(self) -> None:
        cmd = AgentCommand(
            goal_id="g",
            purpose="p",
            kind="terminal.exec",
            command="echo hi",
        )
        encoded = serialize_command_payload(cmd)
        decoded = deserialize_command(encoded)
        self.assertEqual(decoded, cmd)


class ResultSerializationTests(unittest.TestCase):
    def _make_result(self) -> AgentCommandResult:
        return AgentCommandResult(
            command_id="cmd-1",
            goal_id="goal-1",
            status="completed",
            success=True,
            policy_decision=_decision(True),
        )

    def test_serialize_result_payload_is_stable(self) -> None:
        result = self._make_result()
        a = serialize_result_payload(result)
        b = serialize_result_payload(result)
        self.assertEqual(a, b)

    def test_deserialize_result_round_trip(self) -> None:
        result = self._make_result()
        encoded = serialize_result_payload(result)
        decoded = deserialize_result(encoded)
        self.assertEqual(decoded.command_id, "cmd-1")
        self.assertEqual(decoded.status, "completed")
        self.assertTrue(decoded.policy_decision.allowed)

    def test_result_to_wire_dict_is_json_safe(self) -> None:
        result = self._make_result()
        wire = result_to_wire_dict(result)
        self.assertEqual(wire["command_id"], "cmd-1")
        self.assertEqual(wire["status"], "completed")
        # The wire dict must NOT carry the auto-derived ``policy_decision_summary``
        # unless it was explicitly populated. By default the model_validator
        # populates it, so it IS present in the wire payload.
        self.assertIn("policy_decision_summary", wire)
        self.assertEqual(wire["policy_decision_summary"]["action"], "allow")


if __name__ == "__main__":
    unittest.main()
