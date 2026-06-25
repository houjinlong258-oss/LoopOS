"""FusionOptimizer: orchestrate candidates, critique, verifier, Mad Dog, resolver.

The optimizer is a **pure function** in v0.4.0: it does not dispatch
a syscall, write a file, or call a paid provider. It produces a
``FusionOptimizationResult`` and stops.

The five roles:

* ``planner``    — generate ``PlanCandidate`` objects
* ``critic``     — produce ``ReviewFinding`` against a candidate
* ``verifier``   — cross-check candidate against findings
* ``mad_dog``    — extreme quality attack across 10 categories
* ``resolver``   — merge surviving candidates into a single next plan
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from loopos.fusion_optimizer.candidates import rank_candidates
from loopos.fusion_optimizer.critique import CritiqueEngine
from loopos.fusion_optimizer.mad_dog import MadDogFinding, MadDogReviewer
from loopos.fusion_optimizer.models import (
    FusionOptimizationRequest,
    FusionOptimizationResult,
)
from loopos.fusion_optimizer.resolver import Resolver
from loopos.fusion_optimizer.verifier import EvidenceVerifier
from loopos.loop_engine.models import PlanCandidate, ReviewFinding


class FusionOptimizer:
    """The v0.4.0 fusion optimizer."""

    def __init__(
        self,
        critic: CritiqueEngine | None = None,
        verifier: EvidenceVerifier | None = None,
        mad_dog: MadDogReviewer | None = None,
        resolver: Resolver | None = None,
        candidate_factory: Callable[
            [FusionOptimizationRequest], Iterable[PlanCandidate]
        ] | None = None,
    ) -> None:
        self.critic = critic or CritiqueEngine()
        self.verifier = verifier or EvidenceVerifier()
        self.mad_dog = mad_dog or MadDogReviewer()
        self.resolver = resolver or Resolver()
        self._candidate_factory = candidate_factory

    def optimize(
        self,
        request: FusionOptimizationRequest,
    ) -> FusionOptimizationResult:
        # 1. Ensure we have candidates.
        candidates: list[PlanCandidate] = list(request.candidates)
        if not candidates:
            candidates = self._default_candidates(request)

        # 2. Critique each.
        findings: list[ReviewFinding] = []
        for c in candidates:
            findings.extend(self.critic.critique(c, request.success_criteria))

        # 3. Mad Dog attack (only on the latest iteration's outcome,
        #    not on a candidate per se).
        prior = request.previous_iteration
        if prior is not None:
            for mdf in self.mad_dog.review(
                request.current_state,
                prior.plan,
                prior.build_result,
                prior.test_result,
            ):
                findings.extend(_maddog_to_review_findings(mdf))

        # 4. Verify each candidate's evidence.
        valid_candidates: list[PlanCandidate] = []
        for c in candidates:
            ok, _problems = self.verifier.verify(c, findings, request.success_criteria)
            if ok:
                valid_candidates.append(c)
        if not valid_candidates:
            valid_candidates = candidates  # degrade gracefully

        # 5. Rank.
        ranked = rank_candidates(valid_candidates, request.success_criteria)
        top = ranked[0] if ranked else candidates[0]
        top_score = float(ranked.index(top)) if top in ranked else 0.0

        # 6. Resolve.
        recommended, disagreements = self.resolver.resolve(ranked, top_score)

        # 7. Optional repair / optimization plan from prior iteration.
        repair_plan = prior.repair_plan if prior is not None else None
        opt_plan = prior.optimization_plan if prior is not None else None

        confidence = _confidence(len(candidates), len(findings))
        token_cost = _estimate_plan_tokens(recommended)
        expected_gain = _expected_quality_gain(findings)
        utility_score = max(0.0, expected_gain - (token_cost / 10000.0))
        return FusionOptimizationResult(
            recommended_next_plan=recommended,
            alternatives=ranked[1:],
            review_findings=findings,
            repair_plan=repair_plan,
            optimization_plan=opt_plan,
            rationale=(
                f"Selected '{recommended.title}' from {len(candidates)} candidate(s) "
                f"using {request.mode} mode."
            ),
            disagreements=disagreements,
            confidence=round(confidence, 4),
            mode=request.mode,
            token_cost_estimate=token_cost,
            expected_quality_gain=round(expected_gain, 4),
            utility_score=round(utility_score, 4),
        )

    def _default_candidates(self, request: FusionOptimizationRequest) -> list[PlanCandidate]:
        # No LLM in v0.4.0; produce a single baseline candidate from the
        # current state. Real LLM-driven candidate generation is a
        # v0.4.x pluggable concern.
        if self._candidate_factory is not None:
            return list(self._candidate_factory(request))
        goal_text = request.goal.normalized_goal or request.goal.raw_goal
        return [
            PlanCandidate(
                title=f"Baseline next plan for: {goal_text}",
                steps=[
                    "Address prior findings (if any)",
                    "Re-run tests and review",
                ],
                rationale=(
                    "Default consensus candidate; the optimizer is configured "
                    "without an external candidate factory."
                ),
                expected_outcomes=["Prior findings addressed"],
                success_criteria_refs=[
                    c.id for c in request.success_criteria.items if c.required
                ],
                source="fusion",
            )
        ]


def _confidence(num_candidates: int, num_findings: int) -> float:
    if num_candidates <= 0:
        return 0.0
    # More candidates -> slightly more confidence (we saw more options).
    # More findings -> slightly less confidence (we saw more issues).
    base = 0.5
    base += min(0.3, 0.05 * num_candidates)
    base -= min(0.3, 0.05 * num_findings)
    return max(0.0, min(1.0, base))


def _estimate_plan_tokens(plan: PlanCandidate) -> int:
    text = " ".join([plan.title, plan.rationale, " ".join(plan.steps)])
    return max(1, len(text) // 4)


def _expected_quality_gain(findings: list[ReviewFinding]) -> float:
    if not findings:
        return 0.1
    severity_gain = {"info": 0.01, "low": 0.03, "medium": 0.07, "high": 0.12, "critical": 0.2}
    return min(1.0, sum(severity_gain.get(f.severity, 0.03) for f in findings))


def _maddog_to_review_findings(mdf: MadDogFinding) -> list[ReviewFinding]:
    """Convert a ``MadDogFinding`` to a list of ``ReviewFinding``.

    Mad Dog findings are surface-distinct (they carry an ``attack`` and
    use the Mad Dog category set), but the loop's downstream layers
    consume ``ReviewFinding``. The translation is a pure data mapping.
    """
    return [
        ReviewFinding(
            id=mdf.id,
            category=mdf.category,
            severity=mdf.severity,
            claim=mdf.claim,
            evidence=list(mdf.evidence),
            impact=mdf.attack or "",
            recommended_fix=mdf.required_fix or "",
            blocks_delivery=mdf.blocks_delivery,
            source="mad_dog",
        )
    ]


__all__ = ["FusionOptimizer"]
