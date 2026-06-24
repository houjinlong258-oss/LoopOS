"""Apollo Natural Command Router (LoopOS v0.4, md §4).

Goal-first command surface: the user states a goal and LoopOS plans the
safe, policy-checked commands to satisfy it. This package is the P0.0
deliverable — a deterministic, offline router (no external LLM calls).

Public surface:

* :class:`CommandRegistry` / :func:`default_registry` — manifests.
* :class:`DeterministicIntentResolver` — goal -> intent + candidates.
* :class:`IntentPlanner` — intent -> :class:`ExecutionPlan`.
* :class:`IntentRouter` — plan-first executor for ``loopos do``.
* schema dataclasses + render helpers.
"""

from __future__ import annotations

from loopos.intent.planner import IntentPlanner, resolve_command
from loopos.intent.registry import CommandRegistry, default_registry
from loopos.intent.render import plan_to_dict, render_plan_plain
from loopos.intent.resolver import (
    DeterministicIntentResolver,
    IntentResolverBackend,
    normalize,
)
from loopos.intent.router import ExecutionResult, IntentRouter, StepResult
from loopos.intent.schema import (
    CommandIntent,
    ExecutionPlan,
    IntentResolution,
    OrchestrationMode,
    PlanStep,
    ResolvedCommand,
    RiskLevel,
    TaskIntent,
    TaskType,
)

__all__ = [
    "CommandRegistry",
    "default_registry",
    "DeterministicIntentResolver",
    "IntentResolverBackend",
    "normalize",
    "IntentPlanner",
    "resolve_command",
    "IntentRouter",
    "ExecutionResult",
    "StepResult",
    "plan_to_dict",
    "render_plan_plain",
    "CommandIntent",
    "ExecutionPlan",
    "IntentResolution",
    "OrchestrationMode",
    "PlanStep",
    "ResolvedCommand",
    "RiskLevel",
    "TaskIntent",
    "TaskType",
]
