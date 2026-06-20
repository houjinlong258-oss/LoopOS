import unittest

from pydantic import ValidationError

from loopos.ail import ail_to_instruction, instruction_to_ail, normalize_instruction
from loopos.ail.models import AILInstruction, AILSyscall
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

    def test_legacy_instruction_normalizes_to_kernel_operation(self) -> None:
        legacy = instruction_to_ail(
            make_instruction("EXEC_TERMINAL", "verify", {"cmd": "echo hi"})
        )
        kernel = normalize_instruction(legacy, run_id="run-1", step=3)

        self.assertEqual(legacy.op, "EXEC_TERMINAL")
        self.assertEqual(kernel.op, "TERM.EXEC")
        assert kernel.reason is not None
        self.assertEqual(kernel.reason.code, "verify")
        self.assertEqual(ail_to_instruction(kernel).op, "EXEC_TERMINAL")

    def test_kernel_instruction_and_syscall_roundtrip(self) -> None:
        instruction = AILInstruction(
            run_id="run-1",
            step=1,
            op="FILE.READ",
            reason={"code": "inspect_file", "evidence": ["goal"]},
            args={"path": "README.md"},
        )
        syscall = AILSyscall(
            run_id="run-1",
            instruction_id=instruction.id,
            name="file.read",
            input={"path": "README.md"},
            policy_decision_id="decision-1",
        )

        self.assertEqual(AILInstruction.model_validate_json(instruction.model_dump_json()).op, "FILE.READ")
        self.assertEqual(AILSyscall.model_validate_json(syscall.model_dump_json()).name, "file.read")


if __name__ == "__main__":
    unittest.main()
