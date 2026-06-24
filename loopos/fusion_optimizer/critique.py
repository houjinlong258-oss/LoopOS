"""Critique engine for plan candidates.

The critique engine produces a list of plain ``ReviewFinding`` items
(not ``MadDogFinding``) against a plan candidate. The findings feed
the resolver and the loop's repair / optimization layers.
"""

from __future__ import annotations

from loopos.loop_engine.models import (
    PlanCandidate,
    ReviewFinding,
    SuccessCriteria,
)


class CritiqueEngine:
    """Critique a plan candidate against success criteria."""

    def critique(
        self,
        candidate: PlanCandidate,
        criteria: SuccessCriteria,
    ) -> list[ReviewFinding]:
        findings: list[ReviewFinding] = []
        required = [c for c in criteria.items if c.required]
        refs = set(candidate.success_criteria_refs)
        missing = [c for c in required if c.id not in refs]
        if missing:
            findings.append(
                ReviewFinding(
                    category="user_goal_mismatch",
                    severity="medium",
                    claim=f"Plan does not reference {len(missing)} required criterion(s).",
                    evidence=[f"missing: {[c.id for c in missing]}"],
                    impact="Plan may diverge from the user goal.",
                    recommended_fix="Anchor the plan to specific success criterion IDs.",
                    blocks_delivery=False,
                    source="reviewer",
                )
            )
        if not candidate.rationale:
            findings.append(
                ReviewFinding(
                    category="weak_design",
                    severity="low",
                    claim="Plan has no rationale.",
                    evidence=["plan.rationale is empty"],
                    impact="Plan choices cannot be reviewed.",
                    recommended_fix="Add a plan rationale explaining the chosen approach.",
                    blocks_delivery=False,
                    source="reviewer",
                )
            )
        if not candidate.steps:
            findings.append(
                ReviewFinding(
                    category="fake_completion",
                    severity="high",
                    claim="Plan has no steps.",
                    evidence=["plan.steps is empty"],
                    impact="Plan cannot be executed.",
                    recommended_fix="Add concrete steps to the plan.",
                    blocks_delivery=True,
                    source="reviewer",
                )
            )
        return findings


__all__ = ["CritiqueEngine"]
