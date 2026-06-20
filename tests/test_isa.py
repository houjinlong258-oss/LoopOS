import unittest

from pydantic import ValidationError

from loopos.core.isa import (
    Instruction,
    InstructionSafety,
    ExpectedObservation,
    instruction_to_json,
    parse_instruction,
)


class IsaTests(unittest.TestCase):
    def test_valid_instruction_parses(self) -> None:
        instruction = parse_instruction(
            {
                "op": "EXEC_TERMINAL",
                "reason_code": "demo",
                "args": {"cmd": "echo hello"},
                "safety": {"risk_level": "low", "requires_approval": False},
                "expected_observation": {"success_criteria": ["hello"]},
            }
        )
        self.assertEqual(instruction.op, "EXEC_TERMINAL")
        self.assertEqual(instruction.args["cmd"], "echo hello")

    def test_invalid_op_fails(self) -> None:
        with self.assertRaises(ValidationError):
            Instruction(op="NOPE", reason_code="bad")

    def test_exec_terminal_requires_cmd(self) -> None:
        with self.assertRaises(ValidationError):
            Instruction(op="EXEC_TERMINAL", reason_code="missing", args={})

    def test_terminate_requires_reason(self) -> None:
        with self.assertRaises(ValidationError):
            Instruction(op="TERMINATE", reason_code="missing", args={})

    def test_blocked_risk_requires_approval(self) -> None:
        with self.assertRaises(ValidationError):
            InstructionSafety(risk_level="blocked", requires_approval=False)
        safety = InstructionSafety(risk_level="blocked", requires_approval=True)
        self.assertEqual(safety.risk_level, "blocked")

    def test_json_roundtrip(self) -> None:
        instruction = Instruction(
            op="PLAN",
            reason_code="roundtrip",
            args={"goal": "test"},
            expected_observation=ExpectedObservation(timeout_seconds=3),
        )
        encoded = instruction_to_json(instruction)
        decoded = parse_instruction(encoded)
        self.assertEqual(decoded.id, instruction.id)
        self.assertEqual(decoded.op, "PLAN")


if __name__ == "__main__":
    unittest.main()
