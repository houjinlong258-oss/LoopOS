"""Deterministic MVP policies."""

from __future__ import annotations

from loopos.core.isa import ExpectedObservation, Instruction, make_instruction
from loopos.core.state import LoopState


class DeterministicDemoPolicy:
    """Two-step policy used by tests and CLI dry runs."""

    def next_instruction(self, state: LoopState) -> Instruction:
        if state.step_index == 0:
            return make_instruction(
                "EXEC_TERMINAL",
                "demo_echo",
                {"cmd": "echo hello", "cwd": "."},
                expected_observation=ExpectedObservation(
                    success_criteria=["stdout contains hello"],
                    failure_criteria=["non-zero exit code"],
                    timeout_seconds=5,
                ),
            )
        return make_instruction(
            "TERMINATE",
            "demo_complete",
            {"reason": "deterministic demo policy completed"},
        )
