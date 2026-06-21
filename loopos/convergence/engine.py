"""Deterministic loop convergence decisions."""

from loopos.convergence.models import EvaluationResult, HaltCondition, LoopDecision, ProgressDelta


class ConvergenceEngine:
    def decide(
        self,
        evaluation: EvaluationResult,
        progress: ProgressDelta,
        *,
        approval_required: bool = False,
    ) -> LoopDecision:
        if evaluation.blocked:
            return LoopDecision(
                action="halt_blocked",
                reason_code="convergence.blocked",
                halt=HaltCondition(reached=True, reason_code="policy_blocked"),
            )
        if approval_required:
            return LoopDecision(action="wait_approval", reason_code="convergence.approval")
        if evaluation.missing_information:
            return LoopDecision(action="ask_user", reason_code="convergence.missing_information")
        if evaluation.goal_satisfied:
            return LoopDecision(
                action="halt_success",
                reason_code="convergence.goal_satisfied",
                halt=HaltCondition(reached=True, reason_code="goal_satisfied"),
            )
        if evaluation.regression:
            return LoopDecision(
                action="repair" if evaluation.repairable else "replan",
                reason_code="convergence.regression",
                evidence=evaluation.evidence,
            )
        if progress.repeated_failures > 2:
            return LoopDecision(
                action="halt_failure",
                reason_code="convergence.repeated_failure_limit",
                evidence=progress.evidence,
                halt=HaltCondition(reached=True, reason_code="repeated_failure_limit"),
            )
        if evaluation.failed and evaluation.repairable:
            return LoopDecision(action="repair", reason_code="convergence.repairable_failure")
        if evaluation.failed:
            return LoopDecision(
                action="halt_failure",
                reason_code="convergence.failure",
                halt=HaltCondition(reached=True, reason_code="unrecoverable_failure"),
            )
        if progress.repeated_actions > 1 or progress.no_progress_count > 1:
            return LoopDecision(
                action="replan",
                reason_code="convergence.repeated_action_or_no_progress",
                evidence=progress.evidence,
            )
        if progress.delta <= 0 or progress.repeated_failures > 1:
            return LoopDecision(action="replan", reason_code="convergence.no_progress")
        return LoopDecision(action="continue", reason_code="convergence.progress")
