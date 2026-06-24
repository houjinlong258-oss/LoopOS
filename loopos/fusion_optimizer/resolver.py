"""Resolver: merge / resolve conflicting candidate plans.

The resolver's job is to pick a single recommended plan from a
ranked candidate list, and to record disagreements as plain
strings so the CLI can show them.
"""

from __future__ import annotations

from typing import Iterable

from loopos.loop_engine.models import PlanCandidate


class Resolver:
    """Resolve a list of candidates into one recommended plan."""

    def resolve(
        self,
        candidates: list[PlanCandidate],
        top_score: float,
    ) -> tuple[PlanCandidate, list[str]]:
        if not candidates:
            raise ValueError("Resolver: at least one candidate is required")
        best = candidates[0]
        disagreements: list[str] = []
        for c in candidates[1:]:
            if _disagrees_materially(best, c):
                disagreements.append(
                    f"Alternative '{c.title}' takes a different approach: "
                    f"{c.rationale or '(no rationale)'}"
                )
        return best, disagreements


def _disagrees_materially(a: PlanCandidate, b: PlanCandidate) -> bool:
    a_steps = set(a.steps)
    b_steps = set(b.steps)
    if not a_steps or not b_steps:
        return False
    overlap = len(a_steps & b_steps) / max(len(a_steps), len(b_steps))
    return overlap < 0.5


def summarize(candidates: Iterable[PlanCandidate]) -> list[str]:
    return [f"{c.title} (source={c.source})" for c in candidates]


__all__ = ["Resolver", "summarize"]
