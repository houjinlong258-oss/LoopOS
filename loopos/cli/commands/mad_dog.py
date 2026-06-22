"""CLI command for the ``mad-dog`` alias.

The ``mad-dog`` command is a friendly alias for the Fusion
Router's explicit user-force mode. It maps directly to the
``fusion-router`` family with the following overrides:

* mode -> ``mad_dog``
* trigger.source -> ``user``
* trigger.reason -> ``explicit_user_request``
* trigger.severity -> ``critical`` (overridable via ``--severity``)

Subcommands (registered as ``loopos mad-dog ...``):

* ``loopos mad-dog task.json [--severity LEVEL] [--json]``
* ``loopos mad-dog explain task.json [--json]``
* ``loopos mad-dog escalate --run-id RUN_ID --reason REASON [--json]``

Mad Dog Mode must still obey:

* Policy OS
* Budget limit
* Provider availability
* No destructive actions without approval
* No live provider calls unless allowed

In v0.2 the router is planning-only and never calls a provider
API. The ``--severity`` flag is a per-trigger override so a user
can request ``mad_dog`` without forcing ``critical`` (e.g. for a
soft escalation that still benefits from the full role set).
"""

from __future__ import annotations

import sys
from typing import Any

from loopos.cli.commands.fusion_router import build_default_router
from loopos.fusion_router.models import FusionTrigger


def mad_dog_command(
    action: str = "plan",
    task_arg: str | None = None,
    *,
    run_id: str | None = None,
    reason: str = "explicit_user_request",
    severity: str = "critical",
    json_output: bool = True,
    router: Any = None,
) -> int:
    """Entry point for ``loopos mad-dog <action>``."""

    router = router or build_default_router()

    if action == "plan":
        if not task_arg:
            print("mad-dog plan requires TASK (path or JSON).", file=sys.stderr)
            return 1
        # Build the trigger with the explicit-user-request shape
        # so the router selects ``mad_dog`` regardless of score.
        # The CLI delegates to the standard plan helper but
        # passes an overridden trigger via the JSON payload
        # (``reason`` + ``severity`` + ``source``).
        _cli_plan_with_mad_dog_trigger(
            task_arg, severity=severity, router=router, json_output=json_output,
        )
        return 0
    if action == "explain":
        if not task_arg:
            print("mad-dog explain requires TASK (path or JSON).", file=sys.stderr)
            return 1
        _cli_explain_with_mad_dog_trigger(
            task_arg, severity=severity, router=router, json_output=json_output,
        )
        return 0
    if action == "escalate":
        if not run_id:
            print("mad-dog escalate requires --run-id.", file=sys.stderr)
            return 1
        # Escalate is planning-only; the explicit-user-request
        # trigger is not appropriate here (the user is escalating
        # an existing run, not the immediate task). Fall back to
        # the standard escalate path with severity=critical.
        from loopos.fusion_router.cli import cli_escalate

        cli_escalate(
            run_id=run_id, reason=reason, router=router, json_output=json_output,
        )
        return 0
    print(f"Unknown mad-dog action: {action}", file=sys.stderr)
    return 1


def _cli_plan_with_mad_dog_trigger(
    task_arg: str,
    *,
    severity: str,
    router: Any,
    json_output: bool,
) -> Any:
    """Plan with the canonical ``mad-dog`` trigger shape.

    The standard :func:`cli_plan` reads ``trigger.source`` /
    ``trigger.reason`` from the JSON payload. We override the
    payload here so a user can type ``loopos mad-dog task.json``
    without editing the JSON to set ``reason="explicit_user_request"``.
    """

    from loopos.fusion_router.cli import _read_task_input, _task_profile_from_payload

    data = _read_task_input(task_arg)
    # Override trigger shape. The user can still tweak ``severity``
    # via ``--severity``.
    data["source"] = "user"
    data["reason"] = "explicit_user_request"
    data["severity"] = severity
    data["requested_mode"] = "mad_dog"
    task = _task_profile_from_payload(data)
    trigger = FusionTrigger(
        source="user",
        reason="explicit_user_request",
        severity=severity,  # type: ignore[arg-type]
        requested_mode="mad_dog",
    )
    plan = router.plan(task, trigger)
    if json_output:
        from loopos.fusion_router.cli import emit_json
        emit_json(plan)
    else:
        _print_plan_human(plan)
    return plan


def _cli_explain_with_mad_dog_trigger(
    task_arg: str,
    *,
    severity: str,
    router: Any,
    json_output: bool,
) -> Any:
    """Explain the activation rationale under the ``mad-dog`` trigger shape."""

    from loopos.fusion_router.cli import _read_task_input, _task_profile_from_payload
    from loopos.fusion_router.router import FusionRouter

    data = _read_task_input(task_arg)
    data["source"] = "user"
    data["reason"] = "explicit_user_request"
    data["severity"] = severity
    data["requested_mode"] = "mad_dog"
    task = _task_profile_from_payload(data)
    trigger = FusionRouter.mad_dog_trigger(severity=severity)  # type: ignore[arg-type]
    explanation = router.explain(task, trigger)
    if json_output:
        from loopos.fusion_router.cli import emit_json
        emit_json(explanation)
    else:
        from loopos.fusion_router.cli import _print_explain_human
        _print_explain_human(explanation)
    return explanation


def _print_plan_human(plan: Any) -> None:
    sys.stdout.write(
        f"MadDog Plan - mode={plan.mode} score={plan.fusion_score}\n"
        f"  trigger: source={plan.trigger.source} reason={plan.trigger.reason} "
        f"severity={plan.trigger.severity}\n"
        f"  roles: {', '.join(a.role for a in plan.assignments) or '(empty)'}\n"
        f"  max_rounds: {plan.max_rounds}\n"
        "  recommended ACI commands:\n"
    )
    for command in plan.recommended_aci_commands:
        sys.stdout.write(
            f"    [{command['sequence']}] kind={command['kind']!r} "
            f"purpose={command['purpose']!r} role={command['role']!r}\n"
        )


def _attach_typer(app: Any) -> None:
    """Register the ``mad-dog`` command with a Typer ``app``."""

    typer_mod = app.__class__.__module__ and sys.modules.get(app.__class__.__module__)
    if typer_mod is None:
        return

    @app.command("mad-dog")
    def _typer_mad_dog(
        action: str = typer_mod.Option("plan", "--action"),  # type: ignore[attr-defined]
        task: str | None = typer_mod.Option(None, "--task"),  # type: ignore[attr-defined]
        run_id: str | None = typer_mod.Option(None, "--run-id"),  # type: ignore[attr-defined]
        reason: str = typer_mod.Option("explicit_user_request", "--reason"),  # type: ignore[attr-defined]
        severity: str = typer_mod.Option("critical", "--severity"),  # type: ignore[attr-defined]
        json_output: bool = typer_mod.Option(True, "--json/--human"),  # type: ignore[attr-defined]
    ) -> None:
        raise typer_mod.Exit(  # type: ignore[attr-defined]
            mad_dog_command(
                action=action,
                task_arg=task,
                run_id=run_id,
                reason=reason,
                severity=severity,
                json_output=json_output,
            )
        )


__all__ = [
    "mad_dog_command",
]