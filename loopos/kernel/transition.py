"""Validated process state transitions."""

from __future__ import annotations

from loopos.kernel.models import KernelPhase, KernelRunStatus, RunRecord, utc_now

_ALLOWED: dict[KernelRunStatus, set[KernelRunStatus]] = {
    "pending": {"running", "cancelled", "blocked", "failed"},
    "running": {
        "waiting_approval",
        "repairing",
        "replanning",
        "succeeded",
        "failed",
        "cancelled",
        "blocked",
    },
    "waiting_approval": {"running", "cancelled", "blocked", "failed"},
    "repairing": {"running", "replanning", "failed", "cancelled", "blocked"},
    "replanning": {"running", "failed", "cancelled", "blocked"},
    "succeeded": set(),
    "failed": set(),
    "cancelled": set(),
    "blocked": set(),
}


class TransitionEngine:
    """Enforce the process lifecycle and update its phase atomically."""

    def apply(
        self,
        run: RunRecord,
        status: KernelRunStatus,
        phase: KernelPhase,
        *,
        reason: str | None = None,
    ) -> RunRecord:
        if status != run.status and status not in _ALLOWED[run.status]:
            raise ValueError(f"invalid run transition: {run.status} -> {status}")
        run.status = status
        run.phase = phase
        if reason and status in {"failed", "blocked", "cancelled"}:
            run.errors.append(reason)
        run.updated_at = utc_now()
        return run

