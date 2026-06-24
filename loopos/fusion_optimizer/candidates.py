"""Plan candidate comparison and ranking.

The v0.4.0 candidate scorer is a simple weighted formula:

* +1.0 for each required success criterion the candidate references.
* +0.5 for each non-required criterion the candidate references.
* -0.2 per risk.
* +0.3 if the candidate has a rationale.
* +0.2 if the candidate has expected outcomes.

The score is used to break ties when ``FusionOptimizer`` picks the
recommended next plan. It is **not** an LLM judgment.
"""

from __future__ import annotations

from loopos.loop_engine.models import PlanCandidate, SuccessCriteria


def score_candidate(candidate: PlanCandidate, criteria: SuccessCriteria) -> float:
    score = 0.0
    refs = set(candidate.success_criteria_refs)
    for c in criteria.items:
        if c.id in refs:
            score += 1.0 if c.required else 0.5
    score -= 0.2 * len(candidate.risks)
    if candidate.rationale:
        score += 0.3
    if candidate.expected_outcomes:
        score += 0.2
    if candidate.estimated_iterations is not None:
        score += 0.1
    return round(score, 4)


def rank_candidates(
    candidates: list[PlanCandidate],
    criteria: SuccessCriteria,
) -> list[PlanCandidate]:
    """Return candidates sorted by ``score_candidate`` descending."""
    return sorted(
        candidates,
        key=lambda c: score_candidate(c, criteria),
        reverse=True,
    )


__all__ = ["rank_candidates", "score_candidate"]
