"""Result sub-models for the Agent Command Interface.

This module groups the small Pydantic models that describe what the
runner observed after dispatching a command:

* :class:`PolicyDecisionSummary` - structured summary of a
  Policy OS decision for the result wire.
* :class:`SyscallSummary` - summary of the dispatched syscall.
* :class:`ObservationSummary` - structured observation attached
  to a command result.
* :class:`ProgressSummary` - lightweight progress hint.
* :class:`EvaluationSummary` - lightweight evaluation hint.
* :class:`ConvergenceSummary` - convergence hint attached to a
  command result.

These models are imported by :mod:`loopos.aci.models` (for the
top-level :class:`AgentCommandResult`), by :mod:`loopos.aci.runner`
(for result building), and by :mod:`loopos.aci.result_builders`
(for the helper builders that the runner composes).

They are re-exported from :mod:`loopos.aci.models` so existing
imports of the form ``from loopos.aci.models import SyscallSummary``
keep working unchanged.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Observation / convergence taxonomy
# ---------------------------------------------------------------------------

ObservationKind = Literal[
    "command_result",
    "file_content",
    "git_state",
    "database_result",
    "noop",
]

ConvergenceHint = Literal[
    "continue",
    "repair",
    "replan",
    "ask_user",
    "wait_approval",
    "halt_success",
    "halt_failure",
    "halt_blocked",
    "not_evaluated",
]


# ---------------------------------------------------------------------------
# Stable reason codes used by result sub-models
# ---------------------------------------------------------------------------

REASON_NO_KERNEL_RUNTIME = "aci.no_kernel_runtime"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class PolicyDecisionSummary(BaseModel):
    """Structured summary of a Policy OS decision for the result wire.

    The runner keeps the full :class:`PolicyDecision` on the result
    for audit. This summary is the structured, agent-facing view used
    by downstream consumers such as the ALI FSM.
    """

    model_config = ConfigDict(extra="forbid")

    decision_id: str
    allowed: bool
    action: str
    severity: str = "info"
    risk: str = "low"
    safety_level: str = "L0"
    requires_approval: bool = False
    reason_codes: list[str] = Field(default_factory=list)


class SyscallSummary(BaseModel):
    """Summary of the syscall that the runner dispatched (if any).

    The runner fills this when ``kind`` resolves to a known syscall
    (e.g. ``terminal.exec`` -> ``terminal.exec``). Pure-metadata
    kinds (``provider_select``, ``explain_only``) leave it empty.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    syscall_id: str | None = None
    risk: str = "low"
    requires_approval: bool = False
    side_effecting: bool = False
    success: bool | None = None
    dry_run: bool = False
    duration_ms: int = 0


class ObservationSummary(BaseModel):
    """Structured observation attached to a command result."""

    model_config = ConfigDict(extra="forbid")

    kind: ObservationKind = "command_result"
    success: bool = False
    summary: str = ""
    return_code: int | None = None
    duration_ms: int = 0
    stdout: str = ""
    stderr: str = ""
    data: dict[str, Any] = Field(default_factory=dict)


class ProgressSummary(BaseModel):
    """Lightweight progress hint.

    The runner fills this from runtime evidence when available. When
    the kernel runtime is not yet bound (Phase 1+) the runner emits
    a deterministic placeholder with ``status == "unknown"`` and
    ``reason`` explaining why.
    """

    model_config = ConfigDict(extra="forbid")

    previous_score: float = Field(default=0.0, ge=0.0, le=1.0)
    current_score: float = Field(default=0.0, ge=0.0, le=1.0)
    no_progress: bool = False
    status: str = "unknown"
    reason: str = "kernel integration deferred"
    placeholder: bool = True


class EvaluationSummary(BaseModel):
    """Lightweight evaluation hint.

    The runner never pretends ``goal_satisfied == True`` when no real
    evaluation has run. When the kernel runtime is not bound the
    runner emits ``status == "not_evaluated"`` and reason_code
    ``aci.no_kernel_runtime``.
    """

    model_config = ConfigDict(extra="forbid")

    goal_satisfied: bool = False
    failed: bool = False
    repairable: bool = False
    missing_information: bool = False
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reason_codes: list[str] = Field(default_factory=list)
    status: str = "not_evaluated"
    reason: str = "kernel integration deferred"
    placeholder: bool = True


class ConvergenceSummary(BaseModel):
    """Convergence hint attached to a command result.

    The runner fills this with a real decision when the kernel
    runtime is bound. Until then it emits ``action ==
    "not_evaluated"`` with the kernel-deferred reason code.
    """

    model_config = ConfigDict(extra="forbid")

    action: ConvergenceHint = "not_evaluated"
    reason_code: str = REASON_NO_KERNEL_RUNTIME
    placeholder: bool = True


__all__ = [
    "ConvergenceHint",
    "ConvergenceSummary",
    "EvaluationSummary",
    "ObservationKind",
    "ObservationSummary",
    "PolicyDecisionSummary",
    "ProgressSummary",
    "REASON_NO_KERNEL_RUNTIME",
    "SyscallSummary",
]