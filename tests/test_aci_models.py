"""Tests for ACI models: JSON roundtrip, validation, and required fields."""

from __future__ import annotations

import json
import unittest

from pydantic import ValidationError

from loopos.aci import (
    AgentCommand,
    AgentCommandResult,
    CommandValidationError,
    parse_command,
    serialize_command,
)
from loopos.aci.models import (
    ConvergenceSnapshot,
    EvaluationHint,
    ObservationSummary,
    ProgressSnapshot,
)
from loopos.policy_os.models import PolicyDecision


def _decision(allowed: bool = True) -> PolicyDecision:
    return PolicyDecision(
        allowed=allowed,
        action="allow" if allowed else "deny",
        reason_codes=["aci.test"] if allowed else ["aci.test_denied"],
    )


class AgentCommandModelTests(unittest.TestCase):
    def test_roundtrip_json(self) -> None:
        cmd = AgentCommand(
            goal_id="goal-1",
            purpose="verify tests pass",
            kind="terminal.exec",
            command="pytest -q -m 'not slow'",
            args={"cwd": "."},
            timeout_seconds=60,
        )
        encoded = serialize_command(cmd)
        decoded = parse_command(encoded)
        self.assertEqual(decoded.goal_id, "goal-1")
        self.assertEqual(decoded.kind, "terminal.exec")
        self.assertEqual(decoded.command, "pytest -q -m 'not slow'")
        self.assertEqual(decoded.timeout_seconds, 60)
        self.assertEqual(decoded.metadata, {})

    def test_roundtrip_from_dict(self) -> None:
        payload = {
            "goal_id": "goal-dict",
            "purpose": "demo",
            "kind": "file.read",
            "command": "README.md",
        }
        cmd = parse_command(payload)
        self.assertEqual(cmd.kind, "file.read")
        self.assertEqual(cmd.command, "README.md")
        self.assertEqual(cmd.args, {})

    def test_missing_required_field_fails(self) -> None:
        with self.assertRaises(ValidationError):
            AgentCommand(
                goal_id="",
                purpose="x",
                kind="terminal.exec",
                command="echo",
            )
        with self.assertRaises(ValidationError):
            AgentCommand(
                goal_id="g",
                purpose="",
                kind="terminal.exec",
                command="echo",
            )
        with self.assertRaises(ValidationError):
            AgentCommand(
                goal_id="g",
                purpose="p",
                kind="terminal.exec",
                command="",
            )
        with self.assertRaises(ValidationError):
            AgentCommand(
                goal_id="g",
                purpose="p",
                kind="terminal.exec",
                command="echo",
                timeout_seconds=0,
            )

    def test_invalid_json_raises_validation_error(self) -> None:
        with self.assertRaises(CommandValidationError):
            parse_command("{not valid json")

    def test_dry_run_flag_promotes_mode(self) -> None:
        cmd = AgentCommand(
            goal_id="g",
            purpose="p",
            kind="terminal.exec",
            command="echo hi",
            dry_run=True,
        )
        self.assertEqual(cmd.mode, "dry_run")
        self.assertTrue(cmd.dry_run)

    def test_capability_round_trip(self) -> None:
        cmd = AgentCommand(
            goal_id="g",
            purpose="p",
            kind="database.run_migration",
            command="0001_init",
            capabilities={
                "filesystem_read": False,
                "filesystem_write": True,
                "network": False,
                "database": True,
                "tags": ["migration"],
            },
        )
        self.assertTrue(cmd.capabilities.database)
        self.assertEqual(cmd.capabilities.tags, ["migration"])

    def test_serialization_is_stable(self) -> None:
        cmd = AgentCommand(
            goal_id="g",
            purpose="p",
            kind="terminal.exec",
            command="echo hi",
        )
        encoded1 = serialize_command(cmd)
        encoded2 = serialize_command(cmd)
        self.assertEqual(encoded1, encoded2)
        # Round-trips through dict
        payload = json.loads(encoded1)
        self.assertEqual(payload["kind"], "terminal.exec")


class AgentCommandResultModelTests(unittest.TestCase):
    def test_roundtrip_json(self) -> None:
        result = AgentCommandResult(
            command_id="cmd-1",
            goal_id="goal-1",
            status="completed",
            success=True,
            policy_decision=_decision(True),
            observation=ObservationSummary(
                kind="command_result",
                success=True,
                summary="ok",
                return_code=0,
                duration_ms=12,
            ),
            progress=ProgressSnapshot(previous_score=0.5, current_score=0.75),
            evaluation=EvaluationHint(goal_satisfied=True, confidence=0.9),
            convergence=ConvergenceSnapshot(action="continue", reason_code="ok"),
            trace_id="trace-1",
        )
        encoded = result.to_json()
        decoded = AgentCommandResult.from_json(encoded)
        self.assertEqual(decoded.command_id, "cmd-1")
        self.assertEqual(decoded.status, "completed")
        self.assertTrue(decoded.success)
        self.assertEqual(decoded.policy_decision.allowed, True)
        self.assertEqual(decoded.observation.return_code, 0)
        self.assertEqual(decoded.progress.current_score, 0.75)
        self.assertEqual(decoded.evaluation.goal_satisfied, True)
        self.assertEqual(decoded.convergence.action, "continue")
        self.assertEqual(decoded.trace_id, "trace-1")

    def test_roundtrip_from_dict(self) -> None:
        payload = {
            "command_id": "cmd-2",
            "goal_id": "goal-2",
            "status": "blocked",
            "success": False,
            "policy_decision": _decision(False).model_dump(mode="json"),
            "blocked_reason": "policy denied",
        }
        result = AgentCommandResult.from_json(payload)
        self.assertEqual(result.status, "blocked")
        self.assertFalse(result.success)
        self.assertEqual(result.blocked_reason, "policy denied")
        self.assertFalse(result.policy_decision.allowed)

    def test_extra_fields_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            AgentCommandResult.model_validate(
                {
                    "command_id": "x",
                    "goal_id": "g",
                    "status": "completed",
                    "success": True,
                    "policy_decision": _decision(True).model_dump(mode="json"),
                    "extra_unknown": True,
                }
            )


if __name__ == "__main__":
    unittest.main()
