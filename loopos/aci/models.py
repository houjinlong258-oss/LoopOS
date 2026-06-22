"""Typed schemas for the Agent Command Interface.

An :class:`AgentCommand` is the contract an agent submits to LoopOS.
An :class:`AgentCommandResult` is the structured response that the
runtime returns. Both have stable JSON contracts so the wire format
remains testable, replayable, and agent-portable.

Phase 2 extensions (v0.2):
* ``schema_version: Literal["0.2"]`` is carried on every command and
  result so future migrations can be routed.
* :class:`ProviderHint` and :class:`ResolvedProvider` add the
  metadata-only provider binding introduced by the Phase S
  Provider Runtime Registry. (Defined in :mod:`loopos.aci.provider_models`.)
* :class:`RiskHint`, :class:`PolicyDecisionSummary`,
  :class:`SyscallSummary`, :class:`EvaluationSummary`,
  :class:`ProgressSummary`, and :class:`ConvergenceSummary` give the
  agent + the runtime + the ALI FSM consumer a structured view of the
  decision surface, even when the actual evaluation is still
  placeholder. (Defined in :mod:`loopos.aci.result_models`.)
* ``AgentCommandKind`` adds ``provider_select``, ``explain_only``,
  ``file_patch``, and ``git_commit`` so the schema covers the
  full ACI surface; ``AgentCommandStatus`` adds ``unsupported``.

Maintainability note (Phase 3.x):

The provider-binding sub-models (``ProviderHint``, ``ResolvedProvider``,
``CommandCapability``, ``RiskHint``, ``RiskHintLevel``,
``ProviderResolutionSource``) live in :mod:`loopos.aci.provider_models`
and are re-exported here for backward compatibility. The result
sub-models (``PolicyDecisionSummary``, ``SyscallSummary``,
``ObservationSummary``, ``ObservationKind``, ``EvaluationSummary``,
``ProgressSummary``, ``ConvergenceSummary``, ``ConvergenceHint``) live
in :mod:`loopos.aci.result_models` and are re-exported here for
backward compatibility. Existing imports of the form
``from loopos.aci.models import ProviderHint`` keep working
unchanged.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from loopos.policy_os.models import PolicyDecision

# Re-export the provider binding sub-models so existing
# ``from loopos.aci.models import ProviderHint`` style imports keep
# working unchanged.
from loopos.aci.provider_models import (
    CommandCapability,
    ProviderHint,
    ProviderResolutionSource,
    ResolvedProvider,
    RiskHint,
    RiskHintLevel,
)

# Re-export the result sub-models so existing
# ``from loopos.aci.models import SyscallSummary`` style imports keep
# working unchanged. ``REASON_NO_KERNEL_RUNTIME`` is also re-exported
# so external callers can read the same constant.
from loopos.aci.result_models import (
    ConvergenceHint,
    ConvergenceSummary,
    EvaluationSummary,
    ObservationKind,
    ObservationSummary,
    PolicyDecisionSummary,
    ProgressSummary,
    REASON_NO_KERNEL_RUNTIME,
    SyscallSummary,
)

# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------

ACISchemaVersion = Literal["0.2"]


# ----- Command taxonomy ---------------------------------------------------

AgentCommandKind = Literal[
    "terminal.exec",
    "file.read",
    "file.write",
    "file.patch",
    "git.status",
    "git.diff",
    "git.commit",
    "database.query",
    "database.run_migration",
    "provider_select",
    "explain_only",
    "noop",
]

AgentCommandMode = Literal["guarded", "dry_run"]

AgentCommandStatus = Literal[
    "completed",
    "blocked",
    "failed",
    "approval_required",
    "dry_run",
    "unsupported",
]


# ----- Stable reason codes -----------------------------------------------

REASON_PROVIDER_NOT_FOUND = "provider_not_found"
REASON_PROVIDER_CAPABILITY_UNAVAILABLE = "provider_capability_unavailable"
REASON_PROVIDER_LOCAL_ONLY_REQUIRED = "provider_local_only_required"
REASON_PROVIDER_FALLBACK_NOT_ALLOWED = "provider_fallback_not_allowed"
REASON_POLICY_DENIED = "policy_denied"
REASON_POLICY_REQUIRES_APPROVAL = "policy_requires_approval"
REASON_CAPABILITY_BOUNDARY_DENIED = "capability_boundary_denied"
REASON_FREEDOM_BUDGET_DENIED = "freedom_budget_denied"
REASON_UNSUPPORTED_COMMAND_KIND = "unsupported_command_kind"
REASON_DRY_RUN_NO_SIDE_EFFECT = "dry_run_no_side_effect"
REASON_SYSCALL_FAILED = "syscall_failed"
REASON_OBSERVATION_MISSING = "observation_missing"
REASON_TRACE_REQUIRED = "trace_required"
REASON_INVALID_COMMAND = "invalid_command"
REASON_TERMINAL_RM_RF_DENIED = "terminal_rm_rf_denied"
REASON_REMOTE_SCRIPT_PIPE_DENIED = "remote_script_pipe_denied"
REASON_GIT_TAG_DENIED = "git_tag_denied"
REASON_RELEASE_EVIDENCE_MUTATION_DENIED = "release_evidence_mutation_denied"
REASON_NETWORK_ACCESS_DENIED = "network_access_denied"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ----- Top-level models ---------------------------------------------------


class AgentCommand(BaseModel):
    """Single agent command submitted to the ACI layer.

    Required fields (kept for backward compatibility with the v0.1
    callers): ``goal_id``, ``purpose``, ``kind``, ``command``.

    Phase 2 additions:

    * ``schema_version`` -- wire-format discriminator.
    * ``session_id`` -- optional ALI session binding.
    * ``intent`` -- human-readable one-line intent.
    * ``cwd`` -- optional working directory override.
    * ``provider_hint`` -- optional :class:`ProviderHint`.
    * ``risk_hint`` -- optional :class:`RiskHint`.
    * ``trace_required`` -- defaults to True; the runner surfaces a
      ``trace_required`` reason_code when it cannot produce trace
      evidence.
    * ``outcome_contract_id`` -- optional OutcomeContract reference.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: ACISchemaVersion = "0.2"
    id: str = Field(default_factory=lambda: str(uuid4()))
    goal_id: str
    purpose: str
    kind: AgentCommandKind
    intent: str = ""
    command: str
    args: dict[str, Any] = Field(default_factory=dict)
    cwd: str | None = None
    session_id: str | None = None
    outcome_contract_id: str | None = None
    provider_hint: ProviderHint | None = None
    risk_hint: RiskHint | None = None
    mode: AgentCommandMode = "guarded"
    capabilities: CommandCapability = Field(default_factory=CommandCapability)
    timeout_seconds: int | None = Field(default=None, ge=1)
    expected_observation: str = "command_result"
    approval_granted: bool = False
    dry_run: bool = False
    trace_required: bool = True
    created_at: datetime = Field(default_factory=_utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("goal_id", "purpose", "kind")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("value is required and must be non-empty")
        return value

    @field_validator("expected_observation")
    @classmethod
    def observation_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("expected_observation is required")
        return value

    @model_validator(mode="after")
    def dry_run_sets_mode(self) -> "AgentCommand":
        if self.dry_run and self.mode != "dry_run":
            object.__setattr__(self, "mode", "dry_run")
        return self

    @model_validator(mode="after")
    def command_required_for_execution_kinds(self) -> "AgentCommand":
        # The ``command`` field may be empty for kinds that do not
        # execute a shell-style command (``noop``, ``provider_select``,
        # ``explain_only``). For all other kinds the agent MUST
        # supply a non-empty command string.
        no_command_kinds = frozenset({"noop", "provider_select", "explain_only"})
        if self.kind not in no_command_kinds and not self.command.strip():
            raise ValueError(
                f"command is required for kind={self.kind!r}"
            )
        return self

    @model_validator(mode="after")
    def provider_select_must_carry_hint(self) -> "AgentCommand":
        # When kind == "provider_select", the agent MUST supply a
        # provider_hint; otherwise there is nothing to resolve.
        if self.kind == "provider_select" and self.provider_hint is None:
            raise ValueError(
                "kind='provider_select' requires a provider_hint"
            )
        return self


class AgentCommandResult(BaseModel):
    """Structured response returned by the ACI runner.

    Backward-compatible with the v0.1 contract. Phase 2 additions:

    * ``schema_version`` -- wire-format discriminator.
    * ``session_id`` -- optional ALI session binding.
    * ``resolved_provider`` -- populated when the runner resolved a
      :class:`ProviderHint`.
    * ``syscall`` -- :class:`SyscallSummary` for the dispatched syscall.
    * ``reason_codes`` -- top-level stable codes for ALI consumption.
    * ``messages`` -- human-readable diagnostics (may change between
      versions; ``reason_codes`` are stable).
    * ``policy_decision_summary`` -- structured summary for downstream
      consumers. The full :class:`PolicyDecision` is still kept on
      ``policy_decision`` for audit / replay.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: ACISchemaVersion = "0.2"
    command_id: str
    goal_id: str
    session_id: str | None = None
    status: AgentCommandStatus
    success: bool = False

    resolved_provider: ResolvedProvider | None = None
    policy_decision: PolicyDecision
    policy_decision_summary: PolicyDecisionSummary | None = None
    syscall: SyscallSummary | None = None
    observation: ObservationSummary = Field(default_factory=ObservationSummary)
    evaluation: EvaluationSummary = Field(default_factory=EvaluationSummary)
    progress: ProgressSummary = Field(default_factory=ProgressSummary)
    convergence: ConvergenceSummary = Field(default_factory=ConvergenceSummary)

    trace_id: str | None = None
    reason_codes: list[str] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)
    blocked_reason: str | None = None
    requires_approval: bool = False
    dry_run: bool = False
    created_at: datetime = Field(default_factory=_utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("status")
    @classmethod
    def status_consistent(cls, value: AgentCommandStatus) -> AgentCommandStatus:
        return value

    @model_validator(mode="after")
    def populate_policy_summary(self) -> "AgentCommandResult":
        # Auto-derive ``policy_decision_summary`` from ``policy_decision``
        # when the caller did not supply it explicitly.
        if self.policy_decision_summary is None:
            self.policy_decision_summary = PolicyDecisionSummary(
                decision_id=self.policy_decision.decision_id,
                allowed=self.policy_decision.allowed,
                action=self.policy_decision.action,
                severity=self.policy_decision.severity,
                risk=self.policy_decision.risk,
                safety_level=self.policy_decision.safety_level,
                requires_approval=self.policy_decision.requires_approval,
                reason_codes=list(self.policy_decision.reason_codes),
            )
        return self

    def to_json(self) -> str:
        return self.model_dump_json(exclude_none=True)

    @classmethod
    def from_json(cls, raw: str | bytes | dict[str, Any]) -> "AgentCommandResult":
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        if isinstance(raw, str):
            data = json.loads(raw)
        else:
            data = raw
        return cls.model_validate(data)


def parse_command(raw: str | dict[str, Any]) -> AgentCommand:
    """Parse a JSON string or mapping into an :class:`AgentCommand`."""

    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            from loopos.aci.errors import CommandValidationError

            raise CommandValidationError(f"command is not valid JSON: {exc}") from exc
    else:
        data = raw
    return AgentCommand.model_validate(data)


def serialize_command(command: AgentCommand) -> str:
    """Return a stable JSON representation of an :class:`AgentCommand`."""

    return command.model_dump_json(exclude_none=True)


# ---------------------------------------------------------------------------
# Backward-compatibility aliases (v0.1 callers may import these names).
# ---------------------------------------------------------------------------

ProgressSnapshot = ProgressSummary
"""Backward-compat alias kept for the v0.1 test suite."""

EvaluationHint = EvaluationSummary
"""Backward-compat alias kept for the v0.1 test suite."""

ConvergenceSnapshot = ConvergenceSummary
"""Backward-compat alias kept for the v0.1 test suite."""


__all__ = [
    # Schema version
    "ACISchemaVersion",
    # Command taxonomy
    "AgentCommandKind",
    "AgentCommandMode",
    "AgentCommandStatus",
    # Provider binding
    "CommandCapability",
    "ProviderHint",
    "ProviderResolutionSource",
    "ResolvedProvider",
    "RiskHint",
    "RiskHintLevel",
    # Result sub-models
    "ConvergenceHint",
    "ConvergenceSummary",
    "EvaluationSummary",
    "ObservationKind",
    "ObservationSummary",
    "PolicyDecisionSummary",
    "ProgressSummary",
    "SyscallSummary",
    # Stable reason codes
    "REASON_CAPABILITY_BOUNDARY_DENIED",
    "REASON_DRY_RUN_NO_SIDE_EFFECT",
    "REASON_FREEDOM_BUDGET_DENIED",
    "REASON_GIT_TAG_DENIED",
    "REASON_INVALID_COMMAND",
    "REASON_NETWORK_ACCESS_DENIED",
    "REASON_NO_KERNEL_RUNTIME",
    "REASON_OBSERVATION_MISSING",
    "REASON_POLICY_DENIED",
    "REASON_POLICY_REQUIRES_APPROVAL",
    "REASON_PROVIDER_CAPABILITY_UNAVAILABLE",
    "REASON_PROVIDER_FALLBACK_NOT_ALLOWED",
    "REASON_PROVIDER_LOCAL_ONLY_REQUIRED",
    "REASON_PROVIDER_NOT_FOUND",
    "REASON_RELEASE_EVIDENCE_MUTATION_DENIED",
    "REASON_REMOTE_SCRIPT_PIPE_DENIED",
    "REASON_SYSCALL_FAILED",
    "REASON_TERMINAL_RM_RF_DENIED",
    "REASON_TRACE_REQUIRED",
    "REASON_UNSUPPORTED_COMMAND_KIND",
    # Backward-compat aliases
    "ConvergenceSnapshot",
    "EvaluationHint",
    "ProgressSnapshot",
    # Top-level contracts
    "AgentCommand",
    "AgentCommandResult",
    "parse_command",
    "serialize_command",
]