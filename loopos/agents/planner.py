"""Planner adapters."""

from __future__ import annotations

from loopos.core.isa import Instruction
from loopos.core.policy import DeterministicDemoPolicy
from loopos.core.state import LoopState


class DeterministicPlanner:
    """No-LLM planner used by the MVP."""

    def __init__(self) -> None:
        self.policy = DeterministicDemoPolicy()

    def plan(self, state: LoopState) -> Instruction:
        return self.policy.next_instruction(state)
