"""Loop planner: produces a ``PlanCandidate`` for an iteration.

The planner is deterministic and offline. It inspects the prior
iteration's findings and quality score, and emits a plan whose
``source`` is one of ``planner``, ``repair``, or ``optimization``.
Real LLM-driven planning is a pluggable concern for v0.4.x.
"""

from __future__ import annotations

from typing import Iterable

from loopos.loop_engine.models import (
    LoopIteration,
    LoopState,
    PlanCandidate,
    RepairPlan,
    OptimizationPlan,
    ReviewFinding,
)


class LoopPlanner:
    """Emit a ``PlanCandidate`` for the next iteration."""

    def plan(self, state: LoopState) -> PlanCandidate:
        prior = state.latest_iteration()
        if prior is None:
            return self._initial_plan(state)
        if prior.repair_plan is not None:
            return self._repair_plan(state, prior)
        if prior.optimization_plan is not None:
            return self._optimization_plan(state, prior)
        return self._continuation_plan(state, prior)

    def _initial_plan(self, state: LoopState) -> PlanCandidate:
        goal = state.goal.normalized_goal or state.goal.raw_goal
        return PlanCandidate(
            title=f"Initial plan: {goal}",
            steps=[
                f"Understand the goal: {goal}",
                "Draft a minimal implementation outline",
                "Identify test surface for the change",
            ],
            rationale="First pass through the loop; no prior findings.",
            expected_outcomes=[
                "Initial implementation outline",
                "Initial test surface identified",
            ],
            success_criteria_refs=[c.id for c in state.success_criteria.items if c.required],
            source="planner",
        )

    def _repair_plan(
        self, state: LoopState, prior: LoopIteration
    ) -> PlanCandidate:
        repair = prior.repair_plan
        findings = prior.review_findings
        assert repair is not None
        return PlanCandidate(
            title=f"Repair: address {len(repair.source_findings)} findings",
            steps=list(repair.steps) or ["Address the open findings"],
            rationale=(
                f"Repairing findings from iteration {prior.index}: "
                f"{', '.join(repair.source_findings) or 'n/a'}"
            ),
            risks=_risks_for(findings),
            expected_outcomes=[repair.expected_fix or "Findings addressed"],
            success_criteria_refs=[
                c.id for c in state.success_criteria.items if c.required
            ],
            source="repair",
        )

    def _optimization_plan(
        self, state: LoopState, prior: LoopIteration
    ) -> PlanCandidate:
        opt = prior.optimization_plan
        assert opt is not None
        return PlanCandidate(
            title=f"Optimize: {opt.target}",
            steps=list(opt.steps) or [f"Optimize {opt.target}"],
            rationale=opt.reason,
            expected_outcomes=[opt.expected_improvement or "Quality improved"],
            success_criteria_refs=[
                c.id for c in state.success_criteria.items if c.required
            ],
            source="optimizer",
        )

    def _continuation_plan(self, state: LoopState, prior: LoopIteration) -> PlanCandidate:
        goal = state.goal.normalized_goal or state.goal.raw_goal
        open_findings = len(prior.review_findings)
        return PlanCandidate(
            title=f"Continuation: {goal}",
            steps=[
                f"Address {open_findings} open findings" if open_findings else "Continue implementation",
                "Re-run tests and review",
            ],
            rationale=(
                "No repair or optimization plan was produced; continuing the loop."
            ),
            success_criteria_refs=[
                c.id for c in state.success_criteria.items if c.required
            ],
            source="planner",
        )


def _risks_for(findings: Iterable[ReviewFinding]) -> list[str]:
    out: list[str] = []
    for f in findings:
        if f.severity in {"high", "critical"}:
            out.append(f"high-severity finding: {f.claim}")
    return out


__all__ = ["LoopPlanner"]


# Re-exports for type checkers
_ = (RepairPlan, OptimizationPlan)
