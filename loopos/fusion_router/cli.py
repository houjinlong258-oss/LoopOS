"""Internal CLI helpers for the Fusion Router.

The :mod:`loopos.cli.commands.fusion_router` and
:mod:`loopos.cli.commands.mad_dog` modules call these helpers to
produce JSON or human-readable output. The helpers do not
register Typer commands themselves; the CLI modules do that.

Why split this out:

* The CLI entry points can stay small (Typer glue + argparse
  option forwarding).
* The output formatting is unit-testable without Typer.
* The router stays Typer-free (Typer is an optional dependency).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from loopos.fusion_router.models import (
    FusionMode,
    FusionPlan,
    FusionTaskProfile,
    FusionTrigger,
)
from loopos.fusion_router.router import FusionRouter


def _read_task_input(task_arg: str) -> dict[str, Any]:
    """Read a task profile from a JSON file path or a JSON string.

    The CLI accepts either ``task.json`` (path) or an inline
    JSON payload. The two share the same :class:`FusionTaskProfile`
    schema.
    """

    candidate = Path(task_arg)
    if candidate.exists() and candidate.is_file():
        raw = candidate.read_text(encoding="utf-8")
    else:
        raw = task_arg
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"fusion: task payload is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("fusion: task payload must be a JSON object")
    return data


def _task_profile_from_payload(
    data: dict[str, Any],
) -> FusionTaskProfile:
    """Map a free-form task payload into a :class:`FusionTaskProfile`."""

    return FusionTaskProfile(
        title=str(data.get("title", "untitled")),
        task_type=str(data.get("task_type", "feature")),  # type: ignore[arg-type]
        goal_id=data.get("goal_id"),
        complexity_score=int(data.get("complexity_score", 0)),
        risk_score=int(data.get("risk_score", 0)),
        failure_count=int(data.get("failure_count", 0)),
        no_progress_count=int(data.get("no_progress_count", 0)),
        user_dissatisfaction_count=int(data.get("user_dissatisfaction_count", 0)),
        affected_files=list(data.get("affected_files", []) or []),
        required_capabilities=list(data.get("required_capabilities", []) or []),
        context_tokens_estimate=data.get("context_tokens_estimate"),
    )


def _trigger_from_payload(
    data: dict[str, Any],
    *,
    default_mode: FusionMode | None = None,
) -> FusionTrigger:
    """Build a :class:`FusionTrigger` from the task payload / CLI overrides."""

    source = str(data.get("source", "user"))  # type: ignore[arg-type]
    reason = str(data.get("reason", "explicit_user_request"))  # type: ignore[arg-type]
    severity = str(data.get("severity", "medium"))  # type: ignore[arg-type]
    requested_mode = data.get("requested_mode", default_mode)
    return FusionTrigger(
        source=source,  # type: ignore[arg-type]
        reason=reason,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        requested_mode=requested_mode,  # type: ignore[arg-type]
        evidence=dict(data.get("evidence", {}) or {}),
    )


def emit_json(payload: Any) -> None:
    """Emit ``payload`` as JSON on stdout."""

    if hasattr(payload, "model_dump_json"):
        sys.stdout.write(payload.model_dump_json(indent=2))
    else:
        sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")


def cli_plan(
    task_arg: str,
    *,
    router: FusionRouter,
    mode: FusionMode | None = None,
    json_output: bool = True,
) -> FusionPlan:
    """Build a :class:`FusionPlan` and emit it.

    The CLI ``fusion-router plan`` and ``mad-dog`` commands both
    call this helper.
    """

    data = _read_task_input(task_arg)
    task = _task_profile_from_payload(data)
    trigger = _trigger_from_payload(data, default_mode=mode)
    plan = router.plan(task, trigger)
    if json_output:
        emit_json(plan)
    else:
        _print_plan_human(plan)
    return plan


def cli_explain(
    task_arg: str,
    *,
    router: FusionRouter,
    mode: FusionMode | None = None,
    json_output: bool = True,
) -> dict[str, Any]:
    """Build the activation rationale and emit it."""

    data = _read_task_input(task_arg)
    task = _task_profile_from_payload(data)
    trigger = _trigger_from_payload(data, default_mode=mode)
    explanation = router.explain(task, trigger)
    if json_output:
        emit_json(explanation)
    else:
        _print_explain_human(explanation)
    return explanation


def cli_dry_run(
    task_arg: str,
    *,
    router: FusionRouter,
    mode: FusionMode | None = None,
    json_output: bool = True,
) -> FusionPlan:
    """Build a plan and emit it. Never dispatches."""

    return cli_plan(task_arg, router=router, mode=mode, json_output=json_output)


def cli_escalate(
    *,
    run_id: str,
    reason: str,
    router: FusionRouter,
    json_output: bool = True,
) -> FusionPlan:
    """Escalate an existing run/session based on failure evidence.

    Builds a synthetic :class:`FusionTaskProfile` from the
    ``run_id`` and the supplied reason, then plans. In v0.2
    there is no persistence layer, so the plan is emitted as
    JSON and the caller can persist / dispatch it through
    ACI / Kernel.
    """

    task = FusionTaskProfile(
        title=f"escalate {run_id}",
        task_type="debugging",
        goal_id=None,
        failure_count=1,
    )
    trigger = FusionRouter.escalate_trigger(
        run_id=run_id,
        reason=reason,  # type: ignore[arg-type]
        severity="high",
    )
    plan = router.plan(task, trigger)
    if json_output:
        emit_json(plan)
    else:
        _print_plan_human(plan)
    return plan


def cli_status(
    fusion_id: str,
    *,
    json_output: bool = True,
) -> dict[str, Any]:
    """Inspect a fusion plan or verdict by id.

    In v0.2 there is no persistence layer; the CLI returns a
    structured ``unsupported`` payload so the caller knows to
    re-run ``plan`` and persist the output themselves.
    """

    payload = {
        "fusion_id": fusion_id,
        "status": "unsupported",
        "note": (
            "v0.2 Fusion Router is planning-only and does not "
            "persist plans. Re-run `fusion-router plan <task> "
            "--json` to regenerate the plan and pipe to a file."
        ),
    }
    if json_output:
        emit_json(payload)
    else:
        sys.stdout.write(
            f"fusion_id: {fusion_id}\n"
            f"status:    {payload['status']}\n"
            f"note:      {payload['note']}\n"
        )
    return payload


def _print_plan_human(plan: FusionPlan) -> None:
    sys.stdout.write(
        f"FusionPlan - mode={plan.mode} score={plan.fusion_score}\n"
        f"  trigger:  source={plan.trigger.source} "
        f"reason={plan.trigger.reason} severity={plan.trigger.severity}\n"
        f"  roles:    {', '.join(a.role for a in plan.assignments) or '(empty)'}\n"
        f"  max_rounds: {plan.max_rounds}\n"
        f"  live_provider_calls_allowed: {plan.live_provider_calls_allowed}\n"
        "  recommended ACI commands:\n"
    )
    for command in plan.recommended_aci_commands:
        sys.stdout.write(
            f"    [{command['sequence']}] kind={command['kind']!r} "
            f"purpose={command['purpose']!r} role={command['role']!r}\n"
        )


def _print_explain_human(explanation: dict[str, Any]) -> None:
    sys.stdout.write(
        f"Fusion Explain - decision={explanation['activation_decision']} "
        f"mode={explanation['selected_mode']} score={explanation['fusion_score']}\n"
        f"  why: {explanation['why_single_or_not']}\n"
        "  trigger reasons:\n"
    )
    for trigger in explanation["trigger_reasons"]:
        sys.stdout.write(
            f"    - source={trigger['source']} reason={trigger['reason']} "
            f"severity={trigger['severity']}\n"
        )
    sys.stdout.write(
        "  required roles:\n"
        + "\n".join(f"    - {role}" for role in explanation["required_roles"])
        + "\n"
    )


__all__ = [
    "cli_dry_run",
    "cli_escalate",
    "cli_explain",
    "cli_plan",
    "cli_status",
]