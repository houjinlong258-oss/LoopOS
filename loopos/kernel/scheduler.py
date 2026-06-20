"""Pure scheduling decisions for LoopOS runs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from loopos.kernel.signals import KernelSignal

ScheduleAction = Literal[
    "continue",
    "wait_approval",
    "repair",
    "replan",
    "halt_succeeded",
    "halt_failed",
    "halt_blocked",
    "halt_cancelled",
]


class SchedulerInput(BaseModel):
    step: int
    max_steps: int
    policy_allowed: bool = True
    approval_required: bool = False
    evaluation_success: bool = False
    evaluation_failed: bool = False
    repairable: bool = False
    no_progress: bool = False
    signal: KernelSignal | None = None


class ScheduleDecision(BaseModel):
    action: ScheduleAction
    reason_code: str


class LoopScheduler:
    """Apply fixed precedence without consulting a model."""

    def decide(self, value: SchedulerInput) -> ScheduleDecision:
        if value.signal == KernelSignal.CANCEL:
            return ScheduleDecision(action="halt_cancelled", reason_code="scheduler.cancelled")
        if not value.policy_allowed or value.signal == KernelSignal.DENY:
            return ScheduleDecision(action="halt_blocked", reason_code="scheduler.policy_blocked")
        if value.approval_required:
            return ScheduleDecision(action="wait_approval", reason_code="scheduler.approval_required")
        if value.evaluation_success:
            return ScheduleDecision(action="halt_succeeded", reason_code="scheduler.success")
        if value.evaluation_failed and value.repairable:
            return ScheduleDecision(action="repair", reason_code="scheduler.repairable_failure")
        if value.no_progress:
            return ScheduleDecision(action="replan", reason_code="scheduler.no_progress")
        if value.step >= value.max_steps:
            return ScheduleDecision(action="halt_failed", reason_code="scheduler.max_steps")
        if value.evaluation_failed:
            return ScheduleDecision(action="halt_failed", reason_code="scheduler.failure")
        return ScheduleDecision(action="continue", reason_code="scheduler.continue")

