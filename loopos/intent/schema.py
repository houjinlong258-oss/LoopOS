"""Apollo Natural Command Router — typed data models (md §4.4).

These dataclasses are immutable and JSON-friendly. They model the
goal-first surface introduced in LoopOS v0.4:

* :class:`TaskIntent` — what LoopOS understood the user wants.
* :class:`CommandIntent` — a registered, deterministic command manifest.
* :class:`ResolvedCommand` — a manifest bound to a concrete argv.
* :class:`PlanStep` / :class:`ExecutionPlan` — the safe, policy-aware
  plan ``loopos plan`` renders and ``loopos do`` may partially execute.

Hard rule (md §4.4): ``authority_delta`` is always ``"none"``. Natural
language can *propose*; LoopOS *plans*; Policy *approves*; only then may
execution happen. Fusion and Mad Dog never raise authority here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

TaskType = Literal[
    "release_readiness",
    "test",
    "lint",
    "typecheck",
    "policy_explain",
    "model_call",
    "workbench",
    "fusion_planning",
    "mad_dog_planning",
    "tool_call",
    "memory",
    "skill",
    "status",
    "doctor",
    "unknown",
]

RiskLevel = Literal["none", "low", "medium", "high", "critical"]
OrchestrationMode = Literal["single", "team", "fusion", "mad_dog"]


@dataclass(frozen=True)
class TaskIntent:
    """The interpreted user goal produced by the resolver."""

    raw_text: str
    normalized_text: str
    task_type: TaskType
    goal: str
    risk_level: RiskLevel
    recommended_mode: OrchestrationMode
    confidence: float
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class CommandIntent:
    """A deterministic, registered command manifest (md §4.5)."""

    command_id: str
    display_name: str
    description: str
    aliases: tuple[str, ...]
    task_types: tuple[TaskType, ...]
    argv_template: tuple[str, ...]
    risk_level: RiskLevel
    network: bool
    spends_budget: bool
    side_effects: bool
    requires_approval: bool
    safe_by_default: bool
    planning_only: bool = False
    example_goals: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResolvedCommand:
    """A :class:`CommandIntent` bound to a concrete argv to run."""

    command_id: str
    display_name: str
    argv: tuple[str, ...]
    risk_level: RiskLevel
    network: bool
    spends_budget: bool
    side_effects: bool
    requires_approval: bool
    safe_by_default: bool
    planning_only: bool
    reason: str


@dataclass(frozen=True)
class PlanStep:
    """A single step in an :class:`ExecutionPlan`."""

    step_id: str
    title: str
    command: ResolvedCommand
    can_execute_now: bool
    blocked_reason: str | None = None


@dataclass(frozen=True)
class ExecutionPlan:
    """The safe, policy-aware plan for a goal.

    ``authority_delta`` is pinned to ``"none"`` — natural language never
    raises authority, not even in fusion or mad_dog mode.
    """

    goal: str
    task_intent: TaskIntent
    mode: OrchestrationMode
    steps: tuple[PlanStep, ...]
    safety_summary: tuple[str, ...]
    approval_required: bool
    dry_run_default: bool = True
    authority_delta: Literal["none"] = "none"


@dataclass(frozen=True)
class IntentResolution:
    """Resolver output: the interpreted intent plus ranked candidates."""

    task_intent: TaskIntent
    primary: CommandIntent | None
    candidates: tuple[CommandIntent, ...] = field(default_factory=tuple)


__all__ = [
    "TaskType",
    "RiskLevel",
    "OrchestrationMode",
    "TaskIntent",
    "CommandIntent",
    "ResolvedCommand",
    "PlanStep",
    "ExecutionPlan",
    "IntentResolution",
]
