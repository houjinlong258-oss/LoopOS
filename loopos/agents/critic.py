"""Evaluation helpers."""

from __future__ import annotations

from loopos.core.isa import Instruction
from loopos.core.state import Evaluation, LoopState, Observation


class RuleBasedCritic:
    """Small critic that mirrors the MVP evaluator contract."""

    def evaluate(
        self,
        state: LoopState,
        instruction: Instruction,
        observation: Observation,
    ) -> Evaluation:
        if instruction.op == "TERMINATE" and observation.success:
            return Evaluation(status="succeeded", score_delta=1.0, summary=observation.summary)
        if not observation.success:
            return Evaluation(status="failed", summary=observation.summary)
        return Evaluation(status="continue", score_delta=0.25, summary=observation.summary)
