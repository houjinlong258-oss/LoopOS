"""Execution planner for the Apollo router (md §4.6, §4.7, §4.8).

The planner turns an :class:`IntentResolution` into an
:class:`ExecutionPlan`: it binds the resolved command to a concrete
argv, marks steps that require approval as blocked, and builds the
safety summary that ``loopos plan`` renders.

Hard rules enforced here:

* ``authority_delta`` stays ``"none"`` (md §4.4).
* steps with ``side_effects`` / ``network`` / ``spends_budget`` /
  ``requires_approval`` are marked ``can_execute_now=False`` and produce
  ``approval_required=True`` (md §4.8). Natural language never bypasses
  approval.
"""

from __future__ import annotations

from pathlib import Path

from loopos.intent.resolver import DeterministicIntentResolver
from loopos.intent.schema import (
    CommandIntent,
    ExecutionPlan,
    IntentResolution,
    PlanStep,
    ResolvedCommand,
)

# Repo root: loopos/intent/planner.py -> parents[2] == repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _argv_has_placeholder(argv: tuple[str, ...]) -> bool:
    return any(token.startswith("<") and token.endswith(">") for token in argv)


def _script_target(argv: tuple[str, ...]) -> str | None:
    """Return the repo-relative script path referenced by argv, if any."""

    for token in argv:
        if token.endswith(".py") and "/" in token:
            return token
    return None


def resolve_command(command: CommandIntent) -> ResolvedCommand:
    """Bind a manifest to a concrete argv (placeholders preserved)."""

    return ResolvedCommand(
        command_id=command.command_id,
        display_name=command.display_name,
        argv=command.argv_template,
        risk_level=command.risk_level,
        network=command.network,
        spends_budget=command.spends_budget,
        side_effects=command.side_effects,
        requires_approval=command.requires_approval,
        safe_by_default=command.safe_by_default,
        planning_only=command.planning_only,
        reason=command.description,
    )


def _blocked_reason(
    command: ResolvedCommand, argv_placeholder: bool, missing_script: str | None
) -> str | None:
    if command.requires_approval:
        return "requires approval (policy-gated side effect)"
    if command.side_effects:
        return "has external side effects; approval required before execution"
    if command.spends_budget:
        return "spends budget; approval required before execution"
    if command.network:
        return "requires network access; explicit opt-in required"
    if argv_placeholder:
        return "command needs concrete arguments before it can run"
    if missing_script is not None:
        return f"target script not present yet: {missing_script}"
    return None


class IntentPlanner:
    """Builds safe, policy-aware execution plans from goals."""

    def __init__(self, resolver: DeterministicIntentResolver | None = None) -> None:
        self._resolver = resolver if resolver is not None else DeterministicIntentResolver()

    @property
    def resolver(self) -> DeterministicIntentResolver:
        return self._resolver

    def plan(self, goal: str) -> ExecutionPlan:
        resolution = self._resolver.resolve(goal)
        return self.plan_from_resolution(resolution)

    def plan_from_resolution(self, resolution: IntentResolution) -> ExecutionPlan:
        task_intent = resolution.task_intent
        steps: list[PlanStep] = []
        safety: list[str] = []
        approval_required = False

        primary = resolution.primary
        if primary is None:
            safety.append("No known command matched this goal; nothing will be executed.")
            return ExecutionPlan(
                goal=task_intent.goal,
                task_intent=task_intent,
                mode=task_intent.recommended_mode,
                steps=(),
                safety_summary=tuple(safety),
                approval_required=False,
                dry_run_default=True,
            )

        resolved = resolve_command(primary)
        argv_placeholder = _argv_has_placeholder(resolved.argv)
        missing_script = self._missing_script(resolved.argv)
        blocked = _blocked_reason(resolved, argv_placeholder, missing_script)
        can_execute_now = blocked is None
        if resolved.requires_approval or resolved.side_effects or resolved.spends_budget:
            approval_required = True

        steps.append(
            PlanStep(
                step_id="step-1",
                title=resolved.display_name,
                command=resolved,
                can_execute_now=can_execute_now,
                blocked_reason=blocked,
            )
        )

        # Safety summary lines (md §4.7).
        if resolved.planning_only:
            safety.append("Planning-only command: no execution, no authority change.")
        if resolved.side_effects:
            safety.append("This action has external side effects and requires approval.")
        if resolved.network:
            safety.append("This action requires network access (explicit opt-in).")
        if resolved.spends_budget:
            safety.append("This action spends budget and requires approval.")
        if not (resolved.side_effects or resolved.network or resolved.spends_budget):
            safety.append("Safe read-only / dry-run command: no external side effects.")
        if task_intent.recommended_mode in ("fusion", "mad_dog"):
            safety.append(
                f"Escalation mode '{task_intent.recommended_mode}' increases intelligence "
                "density, not authority (authority_delta=none)."
            )

        return ExecutionPlan(
            goal=task_intent.goal,
            task_intent=task_intent,
            mode=task_intent.recommended_mode,
            steps=tuple(steps),
            safety_summary=tuple(safety),
            approval_required=approval_required,
            dry_run_default=True,
        )

    def _missing_script(self, argv: tuple[str, ...]) -> str | None:
        target = _script_target(argv)
        if target is None:
            return None
        if (_REPO_ROOT / target).exists():
            return None
        return target


__all__ = ["IntentPlanner", "resolve_command"]
