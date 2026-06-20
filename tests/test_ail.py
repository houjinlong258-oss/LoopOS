import unittest

from pydantic import ValidationError

from loopos.ail import ail_to_instruction, instruction_to_ail
from loopos.ail.models import AILInstruction
from loopos.core.isa import ExpectedObservation, InstructionSafety, make_instruction


class AILTests(unittest.TestCase):
    def test_ai_isa_to_ail_roundtrip(self) -> None:
        instruction = make_instruction("EXEC_TERMINAL", "demo", {"cmd": "echo hi"})

        ail = instruction_to_ail(instruction)
        roundtrip = ail_to_instruction(ail)

        self.assertEqual(ail.op, "EXEC_TERMINAL")
        self.assertEqual(ail.metadata["policy_scope"], "terminal.execute")
        self.assertEqual(roundtrip.args["cmd"], "echo hi")

    def test_terminal_instruction_requires_policy_metadata(self) -> None:
        with self.assertRaises(ValidationError):
            AILInstruction(
                op="EXEC_TERMINAL",
                reason_code="missing_policy",
                args={"cmd": "echo hi"},
                safety=InstructionSafety(),
                expected_observation=ExpectedObservation(),
            )

    def test_call_tool_requires_routing_metadata(self) -> None:
        with self.assertRaises(ValidationError):
            AILInstruction(
                op="CALL_TOOL",
                reason_code="missing_routing",
                args={"tool": "file.read"},
                expected_observation=ExpectedObservation(),
            )

    def test_store_memory_direct_item_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            AILInstruction(
                op="STORE_MEMORY",
                reason_code="direct_memory",
                args={"item": {"content": "remember this"}},
                expected_observation=ExpectedObservation(),
            )


if __name__ == "__main__":
    unittest.main()
