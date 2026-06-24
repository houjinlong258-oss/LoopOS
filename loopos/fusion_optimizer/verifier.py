"""Evidence verification: cross-check candidate evidence against findings.

The verifier is a small, deterministic helper that rejects a
candidate whose evidence is empty for any blocking finding. It
also confirms that the candidate's success-criteria refs are
consistent with the criteria.
"""

from __future__ import annotations

from loopos.loop_engine.models import (
    PlanCandidate,
    ReviewFinding,
    SuccessCriteria,
)


class EvidenceVerifier:
    """Verify evidence for a candidate against prior findings."""

    def verify(
        self,
        candidate: PlanCandidate,
        findings: list[ReviewFinding],
        criteria: SuccessCriteria,
    ) -> tuple[bool, list[str]]:
        problems: list[str] = []
        for f in findings:
            if f.blocks_delivery and not f.evidence:
                problems.append(
                    f"Blocking finding {f.id} ({f.category}) has no evidence."
                )
        valid_refs = {c.id for c in criteria.items}
        for ref in candidate.success_criteria_refs:
            if ref not in valid_refs:
                problems.append(
                    f"Plan references unknown success criterion: {ref}"
                )
        return (not problems), problems


__all__ = ["EvidenceVerifier"]
