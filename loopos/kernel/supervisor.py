"""Kernel supervisor — monitors runs for max steps, timeout, no-progress, and crash recovery."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from loopos.kernel.models import RunRecord


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


SupervisorAction = Literal[
    "continue",
    "pause",
    "resume",
    "cancel",
    "force_checkpoint",
    "halt_timeout",
    "halt_crashed",
    "halt_blocked",
]


class SupervisorDecision(BaseModel):
    """A decision made by the supervisor about a run."""

    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    action: SupervisorAction
    reason_codes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)


class SupervisorConfig(BaseModel):
    """Tunable supervisor thresholds."""
    max_steps: int = 50
    timeout_seconds: float = 600.0
    no_progress_threshold: int = 5
    repeated_failure_threshold: int = 3


class Supervisor:
    """Monitor a run and decide whether to continue, pause, or halt."""

    def __init__(self, config: SupervisorConfig | None = None) -> None:
        self.config = config or SupervisorConfig()

    def evaluate(
        self,
        run: RunRecord,
        *,
        elapsed_seconds: float = 0.0,
        consecutive_no_progress: int = 0,
        consecutive_failures: int = 0,
    ) -> SupervisorDecision:
        run_id = run.run_id

        # Already terminal
        if run.is_terminal:
            return SupervisorDecision(
                run_id=run_id,
                action="continue",
                reason_codes=["supervisor.already_terminal"],
            )

        # Max steps
        if run.step >= self.config.max_steps:
            return SupervisorDecision(
                run_id=run_id,
                action="halt_blocked",
                reason_codes=["supervisor.max_steps_exceeded"],
            )

        # Timeout
        if elapsed_seconds >= self.config.timeout_seconds:
            return SupervisorDecision(
                run_id=run_id,
                action="halt_timeout",
                reason_codes=["supervisor.timeout"],
            )

        # No progress
        if consecutive_no_progress >= self.config.no_progress_threshold:
            return SupervisorDecision(
                run_id=run_id,
                action="halt_blocked",
                reason_codes=["supervisor.no_progress"],
            )

        # Repeated failures
        if consecutive_failures >= self.config.repeated_failure_threshold:
            return SupervisorDecision(
                run_id=run_id,
                action="halt_crashed",
                reason_codes=["supervisor.repeated_failures"],
            )

        return SupervisorDecision(
            run_id=run_id,
            action="continue",
            reason_codes=["supervisor.ok"],
        )

    def force_checkpoint(self, run: RunRecord) -> SupervisorDecision:
        """Request an immediate checkpoint save."""
        return SupervisorDecision(
            run_id=run.run_id,
            action="force_checkpoint",
            reason_codes=["supervisor.manual_checkpoint"],
        )

    def cancel(self, run: RunRecord) -> SupervisorDecision:
        """Request immediate cancellation."""
        return SupervisorDecision(
            run_id=run.run_id,
            action="cancel",
            reason_codes=["supervisor.manual_cancel"],
        )
