"""CLI commands for the Fusion Router.

Subcommands (registered as ``loopos fusion-router ...`` to avoid
clashing with the existing ``loopos fusion ...`` panel-based
fusion command):

* ``loopos fusion-router plan task.json [--json]``
* ``loopos fusion-router explain task.json [--json]``
* ``loopos fusion-router run task.json [--dry-run] [--json]``
* ``loopos fusion-router escalate --run-id RUN_ID --reason REASON [--json]``
* ``loopos fusion-router status FUSION_ID [--json]``

The router is planning-only in v0.2; the CLI does not execute
anything. Use the JSON output to drive downstream ACI / Kernel
dispatch.
"""

from __future__ import annotations

import sys
from typing import Any

from loopos.fusion_router.cli import (
    cli_dry_run,
    cli_escalate,
    cli_explain,
    cli_plan,
    cli_status,
)
from loopos.fusion_router.models import ModelCapabilityProfile
from loopos.fusion_router.router import FusionRouter


def build_default_router() -> FusionRouter:
    """Build a :class:`FusionRouter` with conservative default profiles.

    In v0.2 we do not auto-discover provider capabilities from
    the live registry (the registry is metadata-only and the
    router never calls a provider API). The defaults are
    deliberately conservative: a single ``local`` profile
    marked ``local_only=True`` so the role-assignment tests
    exercise the degradation path under ``no providers``.
    """

    profile = ModelCapabilityProfile(
        provider_id="local-placeholder",
        model_id="local-placeholder",
        local_only=True,
    )
    return FusionRouter(profiles=[profile])


def fusion_router_command(
    action: str = "plan",
    task_arg: str | None = None,
    *,
    run_id: str | None = None,
    reason: str = "repeated_failure",
    fusion_id: str | None = None,
    dry_run: bool = False,
    json_output: bool = True,
    router: FusionRouter | None = None,
) -> int:
    """Entry point for ``loopos fusion-router <action>``."""

    router = router or build_default_router()

    if action == "plan":
        if not task_arg:
            print("fusion-router plan requires TASK (path or JSON).", file=sys.stderr)
            return 1
        cli_plan(task_arg, router=router, json_output=json_output)
        return 0
    if action == "explain":
        if not task_arg:
            print("fusion-router explain requires TASK (path or JSON).", file=sys.stderr)
            return 1
        cli_explain(task_arg, router=router, json_output=json_output)
        return 0
    if action == "run":
        if not task_arg:
            print("fusion-router run requires TASK (path or JSON).", file=sys.stderr)
            return 1
        # ``run`` is planning-only in v0.2; ``--dry-run`` is the
        # default and remains an explicit option for parity with
        # the master prompt's CLI examples.
        cli_dry_run(
            task_arg, router=router, json_output=json_output,
        ) if dry_run else cli_plan(
            task_arg, router=router, json_output=json_output,
        )
        return 0
    if action == "escalate":
        if not run_id:
            print("fusion-router escalate requires --run-id.", file=sys.stderr)
            return 1
        cli_escalate(
            run_id=run_id, reason=reason,
            router=router, json_output=json_output,
        )
        return 0
    if action == "status":
        if not fusion_id:
            print("fusion-router status requires FUSION_ID.", file=sys.stderr)
            return 1
        cli_status(fusion_id, json_output=json_output)
        return 0
    print(f"Unknown fusion-router action: {action}", file=sys.stderr)
    return 1


def _attach_typer(app: Any) -> None:
    """Register the ``fusion-router`` command with a Typer ``app``.

    This helper is invoked from :mod:`loopos.cli.app` once so the
    optional Typer dependency does not leak into the
    :mod:`loopos.fusion_router` package surface.
    """

    typer_mod = app.__class__.__module__ and sys.modules.get(app.__class__.__module__)
    if typer_mod is None:
        return

    @app.command("fusion-router")
    def _typer_fusion_router(
        action: str = typer_mod.Option("plan", "--action"),  # type: ignore[attr-defined]
        task: str | None = typer_mod.Option(None, "--task"),  # type: ignore[attr-defined]
        run_id: str | None = typer_mod.Option(None, "--run-id"),  # type: ignore[attr-defined]
        reason: str = typer_mod.Option("repeated_failure", "--reason"),  # type: ignore[attr-defined]
        fusion_id: str | None = typer_mod.Option(None, "--fusion-id"),  # type: ignore[attr-defined]
        dry_run: bool = typer_mod.Option(False, "--dry-run"),  # type: ignore[attr-defined]
        json_output: bool = typer_mod.Option(True, "--json/--human"),  # type: ignore[attr-defined]
    ) -> None:
        raise typer_mod.Exit(  # type: ignore[attr-defined]
            fusion_router_command(
                action=action,
                task_arg=task,
                run_id=run_id,
                reason=reason,
                fusion_id=fusion_id,
                dry_run=dry_run,
                json_output=json_output,
            )
        )


__all__ = [
    "build_default_router",
    "fusion_router_command",
]