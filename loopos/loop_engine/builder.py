"""Loop builder: produces a ``BuildResult`` for a plan.

In v0.4.0 the builder is **simulated** by default: it does not touch
the filesystem, the network, or any process. A real executor can be
plugged in by setting ``build_fn`` on the constructor.

The simulation is **explicit**: ``BuildResult.status="simulated"``.
The loop engine reads this status and uses it to keep the
simulated / real boundary honest.
"""

from __future__ import annotations

from typing import Callable

from loopos.loop_engine.models import BuildResult, PlanCandidate


class LoopBuilder:
    """Emit a ``BuildResult`` for a plan candidate."""

    def __init__(self, build_fn: Callable[[PlanCandidate], BuildResult] | None = None) -> None:
        self._build_fn = build_fn

    def build(self, plan: PlanCandidate, iteration_id: str, dry_run: bool = True) -> BuildResult:
        if not dry_run and self._build_fn is not None:
            return self._build_fn(plan)
        return self._simulate(plan, iteration_id)

    def _simulate(self, plan: PlanCandidate, iteration_id: str) -> BuildResult:
        return BuildResult(
            iteration_id=iteration_id,
            plan_id=plan.id,
            status="simulated",
            changed_files=[],
            summary=(
                f"Simulated build of '{plan.title}' "
                f"({len(plan.steps)} steps, source={plan.source})."
            ),
            errors=[],
            artifacts=[],
        )


__all__ = ["LoopBuilder"]
