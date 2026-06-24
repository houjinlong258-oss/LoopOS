"""Rendering for the Apollo router (md §4.7).

Two output shapes:

* :func:`render_plan_plain` — human-readable text for ``loopos plan``
  and ``loopos do``.
* :func:`plan_to_dict` — a JSON-safe dict (no Rich markup / control
  characters) for the ``--json`` flag (md §4.7).
"""

from __future__ import annotations

from typing import Any

from loopos.intent.schema import ExecutionPlan, PlanStep, ResolvedCommand


def _command_to_dict(command: ResolvedCommand) -> dict[str, Any]:
    return {
        "command_id": command.command_id,
        "display_name": command.display_name,
        "argv": list(command.argv),
        "risk_level": command.risk_level,
        "network": command.network,
        "spends_budget": command.spends_budget,
        "side_effects": command.side_effects,
        "requires_approval": command.requires_approval,
        "safe_by_default": command.safe_by_default,
        "planning_only": command.planning_only,
        "reason": command.reason,
    }


def _step_to_dict(step: PlanStep) -> dict[str, Any]:
    return {
        "step_id": step.step_id,
        "title": step.title,
        "can_execute_now": step.can_execute_now,
        "blocked_reason": step.blocked_reason,
        "command": _command_to_dict(step.command),
    }


def plan_to_dict(plan: ExecutionPlan) -> dict[str, Any]:
    """Return a JSON-safe representation of a plan (md §4.7)."""

    intent = plan.task_intent
    return {
        "goal": plan.goal,
        "mode": plan.mode,
        "approval_required": plan.approval_required,
        "dry_run_default": plan.dry_run_default,
        "authority_delta": plan.authority_delta,
        "task_intent": {
            "raw_text": intent.raw_text,
            "normalized_text": intent.normalized_text,
            "task_type": intent.task_type,
            "goal": intent.goal,
            "risk_level": intent.risk_level,
            "recommended_mode": intent.recommended_mode,
            "confidence": intent.confidence,
            "reason_codes": list(intent.reason_codes),
        },
        "steps": [_step_to_dict(step) for step in plan.steps],
        "safety_summary": list(plan.safety_summary),
    }


def render_plan_plain(plan: ExecutionPlan) -> str:
    """Return a human-readable plan summary (md §4.7)."""

    intent = plan.task_intent
    lines: list[str] = []
    lines.append("LoopOS Plan")
    lines.append(f"Understood goal : {intent.goal}")
    lines.append(f"Task type       : {intent.task_type}")
    lines.append(f"Recommended mode: {intent.recommended_mode}")
    lines.append(f"Confidence      : {intent.confidence:.2f}")
    lines.append(f"Authority delta : {plan.authority_delta}")
    lines.append("")
    if not plan.steps:
        lines.append("Planned steps   : (none — no known command matched)")
    else:
        lines.append("Planned steps:")
        for step in plan.steps:
            marker = "RUN" if step.can_execute_now else "HOLD"
            lines.append(f"  [{marker}] {step.title}")
            lines.append(f"        command: {' '.join(step.command.argv)}")
            if step.blocked_reason:
                lines.append(f"        blocked: {step.blocked_reason}")
    lines.append("")
    lines.append("Safety summary:")
    for note in plan.safety_summary:
        lines.append(f"  - {note}")
    lines.append("")
    lines.append(f"Approval required: {'yes' if plan.approval_required else 'no'}")
    lines.append(f"Dry-run default  : {'yes' if plan.dry_run_default else 'no'}")
    return "\n".join(lines)


__all__ = ["plan_to_dict", "render_plan_plain"]
