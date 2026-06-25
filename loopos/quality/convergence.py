"""Convergence engine: decide continue / deliver / blocked / budget exhausted.

The convergence decision in v0.4.0 is a ``ConvergenceReport`` — a
typed record that includes the convergence status, the satisfied
criteria, the unsatisfied criteria, and an explicit list of
``FakeConvergenceFinding`` records. The latter is the most
important part: it is the adversarial evaluator's (Mad Dog's)
contribution to the convergence decision. A delivery is only
allowed when ``report.fake_convergence`` is empty.

The decision is a pure function of ``(state, quality, findings)``.
The rules, in order, are:

1. **Required criteria gate.** If any *required* success criterion is
   unsatisfied, return ``continue`` (or ``iteration_budget_exhausted``
   if the budget is gone).
2. **Blocking findings gate.** If any finding has
   ``blocks_delivery=True`` and is backed by evidence, return
   ``continue`` (or ``iteration_budget_exhausted``).
3. **Fake-convergence gate.** If the iteration looks converged but
   any of the following is true, raise a ``FakeConvergenceFinding``
   and stay in ``continue``:
   * success criteria satisfied but ``quality_score.overall`` is below
     the threshold
   * quality score is high but ``goal_alignment`` is low
   * tests are simulated only and no real evidence was produced
   * the loss is flat or rising across the last K iterations
   * a documentation-gap or release-gap blocking finding is open
4. **Quality gate.** If ``overall >= quality_threshold`` and
   ``goal_alignment >= goal_threshold`` and no fake convergence,
   return ``deliver``.
5. **Budget gate.** If ``len(iterations) >= max_iterations``, return
   ``iteration_budget_exhausted``.
6. Otherwise, return ``continue``.

A new ``ProjectLoss`` is computed for the iteration and returned as
part of the report.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from loopos.loop_engine.models import (
    ConvergenceReport,
    ConvergenceStatusLiteral,
    EvaluationSignal,
    FakeConvergenceFinding,
    GoalGap,
    LoopState,
    ProjectLoss,
    ReviewFinding,
    ReviewSeverity,
)
from loopos.quality.models import QualityScore


# Backward-compat alias: ``ConvergenceStatus`` is the v0.4.0-rc name
# for the same record. New code should use ``ConvergenceReport``.
ConvergenceStatus = ConvergenceReport


@dataclass
class ConvergenceDecision:
    """A convergence decision in dataclass form for ergonomic use."""

    status: ConvergenceStatusLiteral
    reason: str
    next_recommended_action: str | None = None


class ConvergenceEngine:
    """Decide whether the loop should keep iterating or converge."""

    def __init__(
        self,
        quality_threshold: float = 0.75,
        goal_threshold: float = 0.60,
        no_progress_window: int = 2,
        no_progress_epsilon: float = 1e-3,
        simulated_acceptable: bool = True,
    ) -> None:
        self.quality_threshold = quality_threshold
        self.goal_threshold = goal_threshold
        # ``no_progress_window`` is the number of consecutive iterations
        # we look at when computing the no-progress gate. If the loss
        # has been flat or rising across this window, we raise a
        # ``no_progress_across_iterations`` fake-convergence finding.
        self.no_progress_window = no_progress_window
        self.no_progress_epsilon = no_progress_epsilon
        # ``simulated_acceptable`` controls whether the fake-convergence
        # detector treats simulated build/test runs as real evidence.
        # The v0.4.0 CLI demo defaults to True so the loop can
        # converge in the simulated MVP. The v0.4.0 readiness check
        # forces this to False so real deployments must produce real
        # evidence.
        self.simulated_acceptable = simulated_acceptable

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def decide(
        self,
        state: LoopState,
        quality: QualityScore | None,
        findings: list[ReviewFinding],
    ) -> ConvergenceReport:
        loss = self.compute_loss(state, quality, findings)
        signals = self._signals_from_findings(findings)

        # 1. Required criteria gate
        unsat = [c for c in state.success_criteria.items if c.required and not c.satisfied]
        if unsat:
            return self._continue_or_budget(
                state,
                reason=f"{len(unsat)} required success criterion(s) unsatisfied.",
                next_action="repair",
                loss=loss,
                signals=signals,
            )

        # 2. Blocking findings gate (evidence-required)
        blocking = [f for f in findings if f.blocks_delivery and f.evidence]
        if blocking:
            # Blocking findings are themselves a fake-convergence signal
            # (we already have a deliverable-looking surface, but a real
            # blocker is open). Surface it.
            fc = [
                FakeConvergenceFinding(
                    category="blocking_finding_with_evidence_open",
                    severity="high",
                    claim=f"{len(blocking)} evidence-backed blocking finding(s) open.",
                    evidence=[f.evidence[0] for f in blocking if f.evidence],
                    required_fix="Address each blocking finding before delivery.",
                )
            ]
            return self._continue_or_budget(
                state,
                reason=f"{len(blocking)} evidence-backed blocking finding(s).",
                next_action="repair",
                loss=loss,
                signals=signals,
                fake=fc,
            )

        # 3. Fake-convergence gate
        fake = self._detect_fake_convergence(state, quality, findings)
        if fake:
            return self._continue_or_budget(
                state,
                reason=(
                    f"Fake convergence detected: {len(fake)} adversarial finding(s)."
                ),
                next_action="optimize",
                loss=loss,
                signals=signals,
                fake=fake,
            )

        # 4. Quality gate
        if quality is not None:
            if (
                quality.overall >= self.quality_threshold
                and quality.goal_alignment >= self.goal_threshold
            ):
                return ConvergenceReport(
                    status="deliver",
                    reason=(
                        f"Quality {quality.overall:.2f} >= threshold "
                        f"{self.quality_threshold:.2f}; "
                        f"goal alignment {quality.goal_alignment:.2f} >= "
                        f"{self.goal_threshold:.2f}; "
                        "no fake convergence."
                    ),
                    satisfied_criteria=[
                        c.id for c in state.success_criteria.items
                    ],
                    unsatisfied_criteria=[],
                    fake_convergence=[],
                    evaluation_signals=signals,
                )

        # 5. Budget gate
        if state.iterations and len(state.iterations) >= state.max_iterations:
            return ConvergenceReport(
                status="iteration_budget_exhausted",
                reason=(
                    f"Reached max_iterations={state.max_iterations} "
                    f"without meeting quality threshold "
                    f"{self.quality_threshold:.2f}."
                ),
                fake_convergence=[],
                evaluation_signals=signals,
            )

        # 6. Continue
        return ConvergenceReport(
            status="continue",
            reason="No required criteria are unsatisfied; quality below threshold.",
            next_recommended_action="optimize",
            fake_convergence=[],
            evaluation_signals=signals,
        )

    # ------------------------------------------------------------------
    # Loss computation
    # ------------------------------------------------------------------

    def compute_loss(
        self,
        state: LoopState,
        quality: QualityScore | None,
        findings: list[ReviewFinding],
        weights: dict[str, float] | None = None,
    ) -> ProjectLoss:
        """Compute the ``ProjectLoss`` for the latest iteration.

        The loss is a weighted sum of four components:

        * ``unsat_required``     — unsatisfied required criteria
        * ``blocking_findings``  — evidence-backed blockers
        * ``no_improvement``     — quality did not improve vs prior
        * ``fake_convergence``   — fake convergence detected

        The defaults are deliberately simple. The weights are exposed
        so projects can tune them; the v0.4.0 loop engine uses the
        defaults.
        """
        w_unsat = (weights or {}).get("unsat_required", 0.40)
        w_block = (weights or {}).get("blocking_findings", 0.30)
        w_noimp = (weights or {}).get("no_improvement", 0.20)
        w_fake = (weights or {}).get("fake_convergence", 0.10)

        # 1. Unsatisfied required criteria
        unsat_ids = [c.id for c in state.success_criteria.items
                     if c.required and not c.satisfied]
        unsat_component = w_unsat * len(unsat_ids)

        # 2. Blocking findings (evidence-backed)
        blocking = [f for f in findings if f.blocks_delivery and f.evidence]
        block_component = w_block * len(blocking)

        # 3. No improvement vs prior iteration
        no_improvement = 0.0
        if (
            quality is not None
            and len(state.iterations) >= 2
            and state.iterations[-2].quality_score is not None
        ):
            prev = state.iterations[-2].quality_score
            if quality.overall - prev.overall < self.no_progress_epsilon:
                no_improvement = w_noimp

        # 4. Fake convergence — same as the gate logic but cheap
        fake = self._detect_fake_convergence(state, quality, findings)
        fake_component = w_fake * len(fake)

        total = unsat_component + block_component + no_improvement + fake_component

        # Delta vs previous
        delta: float | None = None
        if state.iterations:
            prev_loss = getattr(state.iterations[-1], "loss", None)
            if prev_loss is not None:
                delta = total - prev_loss.total

        # Goal gap
        gap = GoalGap(
            unsatisfied_required=unsat_ids,
            blocked_criteria=[f.id for f in blocking],
            goal_alignment=(quality.goal_alignment if quality else 0.0),
            rationale=(
                f"unsat={len(unsat_ids)}, blocking={len(blocking)}, "
                f"no_improvement={int(no_improvement > 0)}, fake={len(fake)}"
            ),
        )

        latest = state.iterations[-1] if state.iterations else None
        return ProjectLoss(
            iteration_id=latest.id if latest else "iter_unknown",
            total=round(total, 4),
            unsat_required=round(unsat_component, 4),
            blocking_findings=round(block_component, 4),
            no_improvement=round(no_improvement, 4),
            fake_convergence=round(fake_component, 4),
            breakdown={
                "unsat_required": round(unsat_component, 4),
                "blocking_findings": round(block_component, 4),
                "no_improvement": round(no_improvement, 4),
                "fake_convergence": round(fake_component, 4),
            },
            goal_gap=gap,
            delta_vs_previous=delta,
        )

    # ------------------------------------------------------------------
    # Fake-convergence detection
    # ------------------------------------------------------------------

    def _detect_fake_convergence(
        self,
        state: LoopState,
        quality: QualityScore | None,
        findings: Iterable[ReviewFinding],
    ) -> list[FakeConvergenceFinding]:
        out: list[FakeConvergenceFinding] = []
        findings_list = list(findings)
        all_required_satisfied = all(
            c.satisfied for c in state.success_criteria.items if c.required
        )

        if all_required_satisfied and quality is not None:
            # a) success criteria passing but quality below threshold
            if quality.overall < self.quality_threshold:
                out.append(FakeConvergenceFinding(
                    category="success_criteria_satisfied_but_quality_gap",
                    severity="high",
                    claim=(
                        f"All required criteria satisfied but quality "
                        f"{quality.overall:.2f} is below threshold "
                        f"{self.quality_threshold:.2f}."
                    ),
                    evidence=[
                        f"quality.overall={quality.overall}",
                        f"quality_threshold={self.quality_threshold}",
                    ],
                    required_fix="Improve the lowest-quality dimension before delivery.",
                ))
            # b) quality high but goal_alignment low
            if quality.overall >= self.quality_threshold and quality.goal_alignment < self.goal_threshold:
                out.append(FakeConvergenceFinding(
                    category="quality_high_but_goal_alignment_low",
                    severity="high",
                    claim=(
                        f"Quality {quality.overall:.2f} is high but "
                        f"goal alignment {quality.goal_alignment:.2f} is below "
                        f"goal threshold {self.goal_threshold:.2f}."
                    ),
                    evidence=[
                        f"quality.goal_alignment={quality.goal_alignment}",
                        f"goal_threshold={self.goal_threshold}",
                    ],
                    required_fix="Tighten the plan to reference all required criteria.",
                ))

        # c) tests passing but documentation / release gap is open
        for f in findings_list:
            if f.category in {"documentation_gap", "release_gap"} and f.severity in {"high", "critical"}:
                out.append(FakeConvergenceFinding(
                    category="tests_passing_but_documentation_gap",
                    severity="high",
                    claim=(
                        f"{f.category} finding is open with severity "
                        f"{f.severity}; tests passing does not equal delivery."
                    ),
                    evidence=f.evidence or [f.claim],
                    required_fix=f.recommended_fix or "Address the gap before delivery.",
                ))

        # d) all tests simulated but no real evidence
        latest = state.iterations[-1] if state.iterations else None
        if latest is not None and not self.simulated_acceptable:
            build = latest.build_result
            tests = latest.test_result
            simulated_only = (
                (build is None or build.status == "simulated")
                and (tests is None or tests.status == "simulated")
            )
            if simulated_only and all_required_satisfied:
                out.append(FakeConvergenceFinding(
                    category="all_tests_simulated_but_no_real_evidence",
                    severity="medium",
                    claim=(
                        "All required criteria are marked satisfied but the "
                        "build and tests are simulated only; no real artifact "
                        "was produced."
                    ),
                    evidence=[
                        f"build.status={build.status if build else None}",
                        f"tests.status={tests.status if tests else None}",
                    ],
                    required_fix=(
                        "Plug in a real LoopBuilder / LoopTester so the "
                        "criteria are backed by real evidence."
                    ),
                ))

        # e) no progress across the last K iterations
        if len(state.iterations) >= self.no_progress_window:
            window = state.iterations[-self.no_progress_window:]
            overalls = [
                it.quality_score.overall for it in window if it.quality_score is not None
            ]
            if len(overalls) >= self.no_progress_window:
                deltas = [overalls[i + 1] - overalls[i] for i in range(len(overalls) - 1)]
                if all(d <= self.no_progress_epsilon for d in deltas):
                    out.append(FakeConvergenceFinding(
                        category="no_progress_across_iterations",
                        severity="medium",
                        claim=(
                            f"Quality did not improve across the last "
                            f"{self.no_progress_window} iterations "
                            f"(deltas={[round(d, 4) for d in deltas]})."
                        ),
                        evidence=[f"overalls={[round(o, 4) for o in overalls]}"],
                        required_fix=(
                            "Change the plan's source / steps; current plan "
                            "is not moving the loss."
                        ),
                    ))

        # f) criteria satisfied only by the simulated-test evidence loop
        # (no human / external evidence). This is the v0.4.0 default
        # but it should be flagged so users know to plug in real tests.
        if all_required_satisfied and state.iterations and not self.simulated_acceptable:
            only_simulated = all(
                (it.test_result is None or it.test_result.status == "simulated")
                and (it.build_result is None or it.build_result.status == "simulated")
                for it in state.iterations
            )
            if only_simulated and not any(
                f.category == "all_tests_simulated_but_no_real_evidence" for f in out
            ):
                out.append(FakeConvergenceFinding(
                    category="criteria_satisfied_by_evidence_loop_only",
                    severity="low",
                    claim=(
                        "Criteria are satisfied only by the simulated test "
                        "evidence loop; no real test ever ran."
                    ),
                    evidence=["all iterations used simulated build/test"],
                    required_fix="Wire a real LoopTester to capture real test runs.",
                ))

        return out

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _signals_from_findings(
        self, findings: Iterable[ReviewFinding]
    ) -> list[EvaluationSignal]:
        out: list[EvaluationSignal] = []
        for f in findings:
            loss_dim = _category_to_loss_dim(f.category)
            out.append(EvaluationSignal(
                id=f"sig_{f.id}",
                source="mad_dog" if f.source == "mad_dog" else "reviewer",
                category=f.category,
                severity=f.severity,
                claim=f.claim,
                evidence=list(f.evidence),
                proposed_step=f.recommended_fix,
                targets_loss_dim=loss_dim,
            ))
        return out

    def _continue_or_budget(
        self,
        state: LoopState,
        reason: str,
        next_action: str,
        loss: ProjectLoss,
        signals: list[EvaluationSignal],
        fake: list[FakeConvergenceFinding] | None = None,
        unsatisfied_criteria: list[str] | None = None,
    ) -> ConvergenceReport:
        fake = fake or []
        unsat = unsatisfied_criteria or [
            c.id for c in state.success_criteria.items
            if c.required and not c.satisfied
        ]
        if state.iterations and len(state.iterations) >= state.max_iterations:
            return ConvergenceReport(
                status="iteration_budget_exhausted",
                reason=reason + " Budget exhausted.",
                next_recommended_action=None,
                unsatisfied_criteria=unsat,
                fake_convergence=fake,
                evaluation_signals=signals,
            )
        return ConvergenceReport(
            status="continue",
            reason=reason,
            next_recommended_action=next_action,
            unsatisfied_criteria=unsat,
            fake_convergence=fake,
            evaluation_signals=signals,
        )


def _category_to_loss_dim(category: str) -> str:
    """Map a ``ReviewFinding.category`` to the loss dimension it affects."""
    mapping = {
        "missing_test": "unsat_required",
        "fake_completion": "fake_convergence",
        "fake_convergence": "fake_convergence",
        "quality_gap": "unsat_required",
        "weak_design": "no_improvement",
        "brittle_flow": "no_improvement",
        "implementation_bug": "blocking_findings",
        "implementation_gap": "blocking_findings",
        "regression_risk": "no_improvement",
        "user_goal_mismatch": "unsat_required",
        "documentation_gap": "blocking_findings",
        "release_gap": "blocking_findings",
        "token_waste": "no_improvement",
        "communication_noise": "no_improvement",
        "visual_verification_gap": "blocking_findings",
        "security_risk": "blocking_findings",
    }
    return mapping.get(category, "unsat_required")


__all__ = [
    "ConvergenceDecision",
    "ConvergenceEngine",
    "ConvergenceStatus",
    "ConvergenceStatusLiteral",
]


# Re-export the severity literal for type checkers
_ = ReviewSeverity
