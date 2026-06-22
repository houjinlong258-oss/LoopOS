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
  Provider Runtime Registry.
* :class:`RiskHint`, :class:`PolicyDecisionSummary`,
  :class:`SyscallSummary`, :class:`EvaluationSummary`,
  :class:`ProgressSummary`, and :class:`ConvergenceSummary` give the
  agent + the runtime + the ALI FSM consumer a structured view of the
  decision surface, even when the actual evaluation is still
  placeholder.
* ``AgentCommandKind`` adds ``provider_select``, ``explain_only``,
  ``file_patch``, and ``git_commit`` so the schema covers the
  full ACI surface; ``AgentCommandStatus`` adds ``unsupported``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from loopos.policy_os.models import PolicyDecision

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

ObservationKind = Literal["command_result", "file_content", "git_state", "database_result", "noop"]

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

ProviderResolutionSource = Literal[
    "exact",
    "capability",
    "local",
    "kind",
    "default",
    "none",
]

RiskHintLevel = Literal["low", "medium", "high", "blocked", "unknown"]


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
REASON_NO_KERNEL_RUNTIME = "aci.no_kernel_runtime"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ----- Sub-models ---------------------------------------------------------


class CommandCapability(BaseModel):
    """Capability hints declared by the agent for a command.

    The runner cross-checks these against the runtime capability
    boundary. A mismatch produces a structured denial, never a
    silent override.
    """

    model_config = ConfigDict(extra="forbid")

    filesystem_read: bool = False
    filesystem_write: bool = False
    network: bool = False
    database: bool = False
    tags: list[str] = Field(default_factory=list)


class ProviderHint(BaseModel):
    """Hint that the agent expresses about which provider to use.

    The hint is consumed by the runner via
    :class:`loopos.providers.ProviderRegistry` and resolved into a
    :class:`ResolvedProvider`. The hint is **declarative**: it
    never triggers a live API call.

    Resolution semantics:

    * ``provider_id`` is set -> exact resolution.
    * ``required_capabilities`` is non-empty -> capability lookup;
      deterministic ordering by provider_id.
    * ``local_only`` is True -> only local profiles considered.
    * ``preferred_kind`` -> filter by transport family after the
      primary lookup.
    * ``allow_fallback`` is False -> silent fallback to a different
      provider is rejected.
    * No match -> reason_code ``provider_not_found`` or
      ``provider_capability_unavailable``.
    """

    model_config = ConfigDict(extra="forbid")

    provider_id: str | None = None
    required_capabilities: list[str] = Field(default_factory=list)
    preferred_kind: str | None = None
    preferred_cost_class: str | None = None
    local_only: bool | None = None
    allow_fallback: bool = False
    notes: str = ""

    @field_validator("provider_id")
    @classmethod
    def _strip_provider_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        return cleaned or None


class ResolvedProvider(BaseModel):
    """Outcome of resolving a :class:`ProviderHint`.

    The runner fills this in :class:`AgentCommandResult.resolved_provider`
    when a hint was supplied or when ``kind == "provider_select"``.

    The ``source`` field tells the agent (and any human reviewer) how
    the resolution was made:

    * ``exact`` -- matched by ``provider_id``.
    * ``capability`` -- matched via :meth:`ProviderRegistry.find_by_capability`.
    * ``local`` -- matched via :meth:`ProviderRegistry.find_local`.
    * ``kind`` -- matched via :meth:`ProviderRegistry.find_by_kind`.
    * ``default`` -- no hint, fell back to a registry default.
    * ``none`` -- no hint supplied.
    """

    model_config = ConfigDict(extra="forbid")

    provider_id: str
    display_name: str | None = None
    kind: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    source: ProviderResolutionSource = "none"
    reason_code: str = ""


class RiskHint(BaseModel):
    """Risk signal declared by the agent for a command.

    The runner forwards this to Policy OS as part of the policy
    request subject; Policy OS remains the source of truth for the
    final risk level. The hint is never authoritative.
    """

    model_config = ConfigDict(extra="forbid")

    level: RiskHintLevel = "unknown"
    reason: str = ""
    tags: list[str] = Field(default_factory=list)


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
