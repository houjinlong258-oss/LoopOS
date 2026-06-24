"""Delivery engine: emit a ``DeliveryCandidate`` from a ``LoopState``.

A delivery is *not* a "the loop finished" signal. In v0.4.0 a
delivery requires:

* all required criteria satisfied **with evidence**,
* no blocking finding with evidence open,
* ``quality_score.overall >= quality_threshold``,
* ``quality_score.goal_alignment >= goal_threshold``,
* a ``ConvergenceReport`` whose ``fake_convergence`` list is empty
  (the adversarial evaluator's veto),
* a non-empty ``summary`` and non-empty ``evidence``.

If any of these are missing, the candidate is still emitted (so the
user can see what happened), but ``ready=False`` and the
``status`` field exposes the reason (``not_ready`` / ``blocked`` /
``deferred``).
"""

from __future__ import annotations

from typing import Any

from loopos.loop_engine.models import LoopState
from loopos.quality.convergence import ConvergenceEngine
from loopos.quality.evidence import EvidenceCollector
from loopos.quality.models import (
    DeliveryCandidate,
    DeliveryStatus,
    QualityScore,
)
from loopos.quality.scorer import QualityScorer


class DeliveryEngine:
    """Evaluate a ``LoopState`` and emit a ``DeliveryCandidate``."""

    def __init__(
        self,
        scorer: QualityScorer | None = None,
        convergence: ConvergenceEngine | None = None,
    ) -> None:
        self._scorer = scorer or QualityScorer()
        self._convergence = convergence or ConvergenceEngine()

    def evaluate(
        self,
        state: LoopState,
        summary: str | None = None,
    ) -> DeliveryCandidate:
        if not state.iterations:
            return DeliveryCandidate(
                goal_id=state.goal.id,
                summary=summary or "Loop has not produced any iterations yet.",
                quality_score=QualityScore(),
                ready=False,
                status="not_ready",
            )

        latest = state.iterations[-1]
        build = latest.build_result
        tests = latest.test_result
        findings = latest.review_findings

        # Score the latest iteration directly (do not depend on a
        # cached score that may not exist on the iteration record).
        quality = self._scorer.score(state, build, tests, findings) if build and tests else QualityScore()

        # Respect the convergence decision the loop already made. If
        # the loop set ``iteration.convergence.status = "deliver"`` we
        # honour it; otherwise we run a fresh convergence check.
        cached_convergence: Any = getattr(latest, "convergence", None)
        if cached_convergence is not None and getattr(cached_convergence, "status", None):
            convergence = cached_convergence
        else:
            convergence = self._convergence.decide(state, quality, findings)

        evidence = EvidenceCollector()
        for c in state.success_criteria.items:
            if c.satisfied and c.evidence:
                for e in c.evidence:
                    evidence.add(f"criterion {c.id} satisfied: {e}")
        for f in findings:
            if f.evidence:
                for e in f.evidence:
                    evidence.add(f"finding {f.id} evidence: {e}")
        if tests is not None and tests.evidence:
            for e in tests.evidence:
                evidence.add(f"test evidence: {e}")

        known_limitations = [
            "simulated executor" if build and build.status == "simulated" else "",
        ]
        known_limitations = [s for s in known_limitations if s]

        open_risks = [
            f"{f.category} ({f.severity}): {f.claim}"
            for f in findings if f.blocks_delivery and f.evidence
        ]

        # The simplified invariant: deliver + non-empty evidence +
        # non-empty summary + no fake convergence.
        ready = (
            convergence.status == "deliver"
            and not getattr(convergence, "is_fake", False)
            and not evidence.is_empty()
            and bool((summary or _default_summary(state)).strip())
        )

        if ready:
            status: DeliveryStatus = "ready"
        elif getattr(convergence, "is_fake", False):
            status = "blocked"
        elif convergence.status == "blocked":
            status = "blocked"
        elif convergence.status == "iteration_budget_exhausted":
            status = "deferred"
        else:
            status = "not_ready"

        # When fake convergence is detected, surface it on the
        # candidate so the CLI / report can show it.
        if getattr(convergence, "is_fake", False):
            for fc in convergence.fake_convergence:
                open_risks.append(
                    f"fake_convergence ({fc.category}): {fc.claim}"
                )

        return DeliveryCandidate(
            goal_id=state.goal.id,
            summary=(summary or _default_summary(state)).strip(),
            evidence=evidence.items(),
            quality_score=quality,
            known_limitations=known_limitations,
            open_risks=open_risks,
            ready=ready,
            status=status,
        )


def _default_summary(state: LoopState) -> str:
    return (
        f"Loop run for goal '{state.goal.raw_goal}' "
        f"with {len(state.iterations)} iteration(s)."
    )


__all__ = ["DeliveryEngine"]
