"""Deterministic test doubles."""

from __future__ import annotations

from collections.abc import Sequence

from loopos.core.isa import Instruction, make_instruction
from loopos.core.state import Observation


class DeterministicMockLLM:
    """Return preloaded instructions without calling an API."""

    def __init__(self, instructions: Sequence[Instruction] | None = None) -> None:
        self.instructions = list(instructions or [])
        self.calls = 0

    def next_instruction(self, prompt: str) -> Instruction:
        self.calls += 1
        if self.instructions:
            return self.instructions.pop(0)
        return make_instruction("TERMINATE", "mock_llm_done", {"reason": "mock LLM exhausted"})


class MockTerminalExecutor:
    """Instruction executor that records commands and returns fixed observations."""

    def __init__(self, *, success: bool = True, stdout: str = "mock\n") -> None:
        self.success = success
        self.stdout = stdout
        self.commands: list[str] = []

    def execute(self, instruction: Instruction) -> Observation:
        command = str(instruction.args.get("cmd", ""))
        self.commands.append(command)
        return Observation(
            success=self.success,
            summary="mock terminal executed" if self.success else "mock terminal failed",
            stdout=self.stdout,
            command=command,
            return_code=0 if self.success else 1,
        )
