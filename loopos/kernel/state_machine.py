"""State-machine facade over transitions and scheduler decisions."""

from __future__ import annotations

from loopos.kernel.models import RunRecord
from loopos.kernel.scheduler import ScheduleDecision
from loopos.kernel.transition import TransitionEngine


class KernelStateMachine:
    def __init__(self, transitions: TransitionEngine | None = None) -> None:
        self.transitions = transitions or TransitionEngine()

    def apply_schedule(self, run: RunRecord, decision: ScheduleDecision) -> RunRecord:
        mapping = {
            "continue": ("running", "EXECUTING"),
            "wait_approval": ("waiting_approval", "WAITING_APPROVAL"),
            "repair": ("repairing", "REPAIRING"),
            "replan": ("replanning", "REPLANNING"),
            "halt_succeeded": ("succeeded", "HALTED"),
            "halt_failed": ("failed", "HALTED"),
            "halt_blocked": ("blocked", "HALTED"),
            "halt_cancelled": ("cancelled", "HALTED"),
        }
        status, phase = mapping[decision.action]
        return self.transitions.apply(run, status, phase, reason=decision.reason_code)  # type: ignore[arg-type]

