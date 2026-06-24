"""Loop optimizer: produces an ``OptimizationPlan`` for non-failing dimensions.

The optimizer is deterministic and offline. It looks for
non-actionable findings (e.g. ``user_goal_mismatch``,
``quality_gap``, ``weak_design``) and emits a single
``OptimizationPlan`` for the highest-priority target. Real
LLM-driven optimization is a v0.4.x pluggable concern.
"""

from __future__ import annotations

from loopos.loop_engine.models import (
    LoopState,
    OptimizationPlan,
    ReviewFinding,
)


class LoopOptimizer:
    """Emit an ``OptimizationPlan`` (or ``None``) for an iteration."""

    def optimize(
        self,
        state: LoopState,
        findings: list[ReviewFinding],
    ) -> OptimizationPlan | None:
        if not findings:
            return None
        # Pick the first non-actionable, non-blocking finding.
        candidates = [
            f for f in findings
            if not f.blocks_delivery
            and f.category in {
                "user_goal_mismatch", "quality_gap", "weak_design",
                "documentation_gap",
            }
        ]
        if not candidates:
            return None
        target = candidates[0]
        return OptimizationPlan(
            target=target.category,
            reason=target.claim,
            expected_improvement=(
                f"Address '{target.category}' to improve overall quality."
            ),
            steps=[
                target.recommended_fix or f"Improve {target.category}",
            ],
            measurable_outcome=(
                f"Reduce {target.category} findings in the next iteration."
            ),
        )


__all__ = ["LoopOptimizer"]
