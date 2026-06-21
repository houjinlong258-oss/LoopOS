"""Convert runtime evidence into deterministic convergence evaluations."""

from __future__ import annotations

from collections.abc import Mapping

from loopos.ail.models import AILInstruction
from loopos.convergence import EvaluationResult
from loopos.kernel.models import RunRecord
from loopos.policy_os.models import PolicyDecision
from loopos.syscalls import SyscallResult


class EvaluationSource:
    """Build an evaluation where observed runtime facts outrank plan hints."""

    def evaluate(
        self,
        *,
        run: RunRecord,
        instruction: AILInstruction | None = None,
        syscall_result: SyscallResult | None = None,
        policy_decision: PolicyDecision | None = None,
        observation: object | None = None,
        hints: Mapping[str, object] | None = None,
    ) -> EvaluationResult:
        values = hints or {}
        step_id = instruction.id if instruction is not None else run.current_instruction_id
        base = {
            "run_id": run.run_id,
            "step_id": step_id,
            "score": _evidence_score(run, syscall_result, values),
        }

        if policy_decision is not None and not policy_decision.allowed:
            return EvaluationResult(
                **base,
                failed=True,
                blocked=True,
                repairable=False,
                failure_type="policy_blocked",
                evidence=list(policy_decision.reason_codes),
                reason_codes=["policy.blocked"],
            )

        if syscall_result is not None:
            if syscall_result.requires_approval and not syscall_result.success:
                return EvaluationResult(
                    **base,
                    missing_information=True,
                    evidence=[syscall_result.error or "approval required"],
                    reason_codes=["approval.required"],
                )
            if not syscall_result.success:
                blocked = syscall_result.risk == "blocked"
                return EvaluationResult(
                    **base,
                    failed=True,
                    blocked=blocked,
                    repairable=not blocked,
                    failure_type="syscall_blocked" if blocked else "syscall_failed",
                    evidence=[syscall_result.error or "syscall failed"],
                    reason_codes=["syscall.blocked" if blocked else "syscall.failed"],
                )
            return EvaluationResult(
                **base,
                goal_satisfied=bool(values.get("goal_satisfied", False)),
                evidence=[f"syscall:{syscall_result.syscall_id}"],
                reason_codes=["syscall.success"],
            )

        observed_success = _observation_success(observation)
        if observed_success is False:
            return EvaluationResult(
                **base,
                failed=True,
                repairable=True,
                failure_type="observation_failed",
                reason_codes=["observation.failed"],
            )

        return EvaluationResult(
            **base,
            goal_satisfied=bool(values.get("goal_satisfied", False)),
            failed=bool(values.get("failed", False)),
            repairable=bool(values.get("repairable", False)),
            missing_information=bool(values.get("missing_information", False)),
            reason_codes=["evaluation.hinted"],
        )


def _evidence_score(
    run: RunRecord,
    syscall_result: SyscallResult | None,
    hints: Mapping[str, object],
) -> float:
    candidates: list[object] = []
    if syscall_result is not None:
        candidates.append(syscall_result.output.get("progress_score"))
    candidates.extend((hints.get("current_score"), hints.get("score")))
    for value in candidates:
        if isinstance(value, int | float) and not isinstance(value, bool):
            return max(0.0, min(1.0, float(value)))
    return run.progress_score


def _observation_success(observation: object | None) -> bool | None:
    if isinstance(observation, Mapping):
        value = observation.get("success")
        return value if isinstance(value, bool) else None
    value = getattr(observation, "success", None)
    return value if isinstance(value, bool) else None
