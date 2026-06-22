"""Typed models for the Fusion Router.

The contracts defined here are the canonical surface for the
Fusion Router. They are Pydantic v2 models with
``extra="forbid"`` so unknown fields are rejected on
construction. The wire format is JSON-compatible so a CLI /
``--json`` output roundtrips without loss.

Design constraints (per master prompt):

* The router is planning-only. No live provider calls are made
  from any model defined here.
* Triggers carry a stable ``source`` and ``reason`` so downstream
  consumers (CLI, Trace bridge, Review) can audit why the router
  escalated.
* Roles, modes, and trigger reasons are Literal types so Pydantic
  rejects unknown values up front.
* All scores are integers clamped via ``Field(ge=..., le=...)``
  so a malformed payload cannot smuggle an out-of-range value.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Taxonomy
# ---------------------------------------------------------------------------

FusionMode = Literal[
    "single",
    "pair",
    "committee",
    "attack",
    "mad_dog",
]

FUSION_MODES: tuple[FusionMode, ...] = (
    "single",
    "pair",
    "committee",
    "attack",
    "mad_dog",
)

FusionRole = Literal[
    "primary",
    "planner",
    "architect",
    "coder",
    "bug_hunter",
    "test_breaker",
    "reviewer",
    "security_guard",
    "simplifier",
    "judge",
    "summarizer",
]

FUSION_ROLES: tuple[FusionRole, ...] = (
    "primary",
    "planner",
    "architect",
    "coder",
    "bug_hunter",
    "test_breaker",
    "reviewer",
    "security_guard",
    "simplifier",
    "judge",
    "summarizer",
)

FusionTriggerSource = Literal[
    "user",
    "ali",
    "kernel",
    "convergence",
    "review",
    "test",
    "release",
]

FUSION_TRIGGER_SOURCES: tuple[FusionTriggerSource, ...] = (
    "user",
    "ali",
    "kernel",
    "convergence",
    "review",
    "test",
    "release",
)

FusionTriggerReason = Literal[
    "explicit_user_request",
    "repeated_failure",
    "no_progress",
    "user_dissatisfaction",
    "high_complexity",
    "large_refactor",
    "nasty_bug",
    "low_confidence",
    "high_risk",
    "release_blocker",
    "security_sensitive",
    "test_flake_or_hidden_failure",
    "model_mismatch",
]

FUSION_TRIGGER_REASONS: tuple[FusionTriggerReason, ...] = (
    "explicit_user_request",
    "repeated_failure",
    "no_progress",
    "user_dissatisfaction",
    "high_complexity",
    "large_refactor",
    "nasty_bug",
    "low_confidence",
    "high_risk",
    "release_blocker",
    "security_sensitive",
    "test_flake_or_hidden_failure",
    "model_mismatch",
)

FusionTriggerSeverity = Literal["low", "medium", "high", "critical"]

FusionTaskType = Literal[
    "bugfix",
    "refactor",
    "feature",
    "audit",
    "release",
    "security",
    "debugging",
    "architecture",
    "test_repair",
]

FusionVerdictStatus = Literal[
    "accepted",
    "rejected",
    "needs_repair",
    "needs_replan",
    "ask_user",
]

FusionVerdictStatus.__doc__ = None  # keep the literal compact for docs


# ---------------------------------------------------------------------------
# Trigger
# ---------------------------------------------------------------------------


class FusionTrigger(BaseModel):
    """A single reason to escalate (or to *not* escalate).

    Multiple triggers can stack on the same plan; the router
    keeps the highest-severity one as the dominant signal.
    """

    model_config = ConfigDict(extra="forbid")

    trigger_id: str = Field(default_factory=lambda: str(uuid4()))
    source: FusionTriggerSource
    reason: FusionTriggerReason
    severity: FusionTriggerSeverity = "medium"
    requested_mode: FusionMode | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Task profile
# ---------------------------------------------------------------------------


class FusionTaskProfile(BaseModel):
    """Structured profile of the task under evaluation.

    Scores are integers on a 0-10 scale; counts are non-negative
    integers; affected files are stable identifiers (relative
    paths, content hashes, or test ids).
    """

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(default_factory=lambda: str(uuid4()))
    goal_id: str | None = None
    title: str
    task_type: FusionTaskType
    complexity_score: int = Field(ge=0, le=10, default=0)
    risk_score: int = Field(ge=0, le=10, default=0)
    failure_count: int = Field(ge=0, default=0)
    no_progress_count: int = Field(ge=0, default=0)
    user_dissatisfaction_count: int = Field(ge=0, default=0)
    affected_files: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    context_tokens_estimate: int | None = None


# ---------------------------------------------------------------------------
# Model capability profile
# ---------------------------------------------------------------------------


class ModelCapabilityProfile(BaseModel):
    """Capability profile for one (provider_id, model_id) pair.

    Scores are integers on a 0-10 scale. Boolean flags expose
    feature support that some roles require (``supports_tools``,
    ``supports_json``, ``supports_long_context``, ``local_only``).

    In v0.2, the registry's existing provider metadata is the
    primary source; missing scores fall back to conservative
    defaults so a profile is always well-formed.
    """

    model_config = ConfigDict(extra="forbid")

    provider_id: str
    model_id: str
    reasoning_score: int = Field(ge=0, le=10, default=5)
    coding_score: int = Field(ge=0, le=10, default=5)
    review_score: int = Field(ge=0, le=10, default=5)
    debugging_score: int = Field(ge=0, le=10, default=5)
    architecture_score: int = Field(ge=0, le=10, default=5)
    security_score: int = Field(ge=0, le=10, default=5)
    test_generation_score: int = Field(ge=0, le=10, default=5)
    context_score: int = Field(ge=0, le=10, default=5)
    speed_score: int = Field(ge=0, le=10, default=5)
    cost_score: int = Field(ge=0, le=10, default=5)
    reliability_score: int = Field(ge=0, le=10, default=5)
    supports_tools: bool = False
    supports_json: bool = True
    supports_long_context: bool = False
    local_only: bool = False


# ---------------------------------------------------------------------------
# Role assignment
# ---------------------------------------------------------------------------


class FusionRoleAssignment(BaseModel):
    """One role in a :class:`FusionPlan`, bound to a provider/model.

    ``capability_score`` is the normalised score (0.0-1.0) the
    router computed for the (role, provider/model) pair.
    ``budget_weight`` is the router's recommended share of the
    FusionPlan's overall budget for this role. ``capability_gaps``
    lists capabilities the chosen model lacks for this role.
    """

    model_config = ConfigDict(extra="forbid")

    role: FusionRole
    provider_id: str
    model_id: str | None = None
    capability_score: float = Field(ge=0.0, le=1.0)
    reason: str
    budget_weight: float = Field(ge=0.0, le=1.0, default=0.0)
    capability_gaps: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------


class FusionPlan(BaseModel):
    """The deterministic, planning-only output of the router.

    ``fusion_score`` is the integer the router computed; ``mode``
    is the mode the score (or an explicit user request) selected;
    ``assignments`` is the deterministic role-to-provider mapping;
    ``recommended_aci_commands`` is the list of structured
    commands (serialised as dicts to keep this model decoupled
    from the ACI package).
    """

    model_config = ConfigDict(extra="forbid")

    fusion_id: str = Field(default_factory=lambda: str(uuid4()))
    mode: FusionMode
    trigger: FusionTrigger
    task_profile: FusionTaskProfile
    fusion_score: int
    assignments: list[FusionRoleAssignment]
    max_rounds: int = Field(ge=1, default=1)
    budget_limit: dict[str, Any] = Field(default_factory=dict)
    stop_conditions: list[str] = Field(default_factory=list)
    recommended_aci_commands: list[dict[str, Any]] = Field(
        default_factory=list,
    )
    trace_required: bool = True
    live_provider_calls_allowed: bool = False


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------


class FusionVerdict(BaseModel):
    """A structured judgment on a :class:`FusionPlan`.

    Verdicts are produced by the router when the operator (or the
    CLI) wants to record whether a plan was accepted, rejected,
    needs repair, needs replan, or asks the user. The verdict
    does not execute anything; it is durable audit evidence.
    """

    model_config = ConfigDict(extra="forbid")

    fusion_id: str
    status: FusionVerdictStatus
    winning_plan_id: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    risks: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    trace_ids: list[str] = Field(default_factory=list)


__all__ = [
    # Taxonomy
    "FUSION_MODES",
    "FUSION_ROLES",
    "FUSION_TRIGGER_REASONS",
    "FUSION_TRIGGER_SOURCES",
    "FusionMode",
    "FusionRole",
    "FusionTaskType",
    "FusionTriggerReason",
    "FusionTriggerSeverity",
    "FusionTriggerSource",
    "FusionVerdictStatus",
    # Models
    "FusionTrigger",
    "FusionTaskProfile",
    "ModelCapabilityProfile",
    "FusionRoleAssignment",
    "FusionPlan",
    "FusionVerdict",
]