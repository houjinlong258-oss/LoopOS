"""CLI commands for the Fusion Router.

Subcommands (registered as ``loopos fusion-router ...`` to avoid
clashing with the existing ``loopos fusion ...`` panel-based
fusion command):

* ``loopos fusion-router plan task.json [--json]``
* ``loopos fusion-router explain task.json [--json]``
* ``loopos fusion-router run task.json [--dry-run] [--json]``
* ``loopos fusion-router escalate --run-id RUN_ID --reason REASON [--json]``
* ``loopos fusion-router status FUSION_ID [--json]``
* ``loopos fusion-router list [--json]``

The router is planning-only in v0.2; the CLI does not execute
anything. ``status`` reads from the local JSON persistence layer
so callers can inspect a previously-built plan or verdict.
Use the JSON output to drive downstream ACI / Kernel dispatch.
"""

from __future__ import annotations

import sys
from typing import Any

from loopos.fusion_router.cli import (
    cli_dry_run,
    cli_escalate,
    cli_explain,
    cli_plan,
)
from loopos.fusion_router.models import ModelCapabilityProfile
from loopos.fusion_router.persistence import FusionPlanStore
from loopos.fusion_router.router import FusionRouter
from loopos.fusion_router.runner import FusionRunner


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


def build_default_store(root: str | None = None) -> FusionPlanStore:
    """Build a :class:`FusionPlanStore` rooted at ``root`` (or ``.loopos/fusion``)."""

    return FusionPlanStore(root=root) if root is not None else FusionPlanStore()


def build_default_runner(
    *,
    kernel_engine: Any = None,
    root: str | None = None,
) -> FusionRunner:
    """Build a :class:`FusionRunner` with the default store."""

    return FusionRunner(
        kernel_engine=kernel_engine,
        store=build_default_store(root),
    )


def cli_status(
    fusion_id: str,
    *,
    store: FusionPlanStore | None = None,
    json_output: bool = True,
) -> dict[str, Any]:
    """Return the persisted plan + verdict for ``fusion_id``.

    The implementation reads from the local JSON store (no DB,
    no network). When the plan or verdict is not found, the
    payload still answers with a structured response so the CLI
    caller can distinguish ``not_found`` from ``error``.
    """

    store = store or build_default_store()
    plan = store.load_plan(fusion_id)
    verdicts = store.load_verdicts(fusion_id)
    if plan is None and not verdicts:
        payload: dict[str, Any] = {
            "fusion_id": fusion_id,
            "status": "not_found",
            "note": (
                "no persisted FusionPlan or FusionVerdict found for this "
                "fusion_id. Re-run `fusion-router plan <task> --json` and "
                "pipe the output to a file, or use the runner adapter to "
                "persist a plan."
            ),
        }
        if json_output:
            from loopos.fusion_router.cli import emit_json
            emit_json(payload)
        else:
            sys.stdout.write(
                f"fusion_id: {fusion_id}\nstatus:    not_found\n"
                f"note:      {payload['note']}\n"
            )
        return payload

    payload = {
        "fusion_id": fusion_id,
        "status": "loaded",
        "plan": plan.model_dump(mode="json") if plan is not None else None,
        "verdicts": [v.model_dump(mode="json") for v in verdicts],
    }
    if json_output:
        from loopos.fusion_router.cli import emit_json
        emit_json(payload)
    else:
        sys.stdout.write(f"fusion_id: {fusion_id}\nstatus:    loaded\n")
        if plan is not None:
            sys.stdout.write(
                f"plan.mode:        {plan.mode}\n"
                f"plan.score:       {plan.fusion_score}\n"
                f"plan.assignments: {len(plan.assignments)}\n"
            )
        if verdicts:
            sys.stdout.write(f"verdicts:         {len(verdicts)}\n")
    return payload


def cli_list(
    *,
    store: FusionPlanStore | None = None,
    json_output: bool = True,
) -> dict[str, Any]:
    """List persisted FusionPlan and FusionVerdict ids."""

    store = store or build_default_store()
    plans = store.list_plans()
    verdicts = store.list_verdicts()
    payload = {
        "plans": plans,
        "verdicts": verdicts,
    }
    if json_output:
        from loopos.fusion_router.cli import emit_json
        emit_json(payload)
    else:
        sys.stdout.write(
            f"plans ({len(plans)}):    {', '.join(plans) or '(none)'}\n"
            f"verdicts ({len(verdicts)}): {', '.join(verdicts) or '(none)'}\n"
        )
    return payload


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
    store: FusionPlanStore | None = None,
    kernel_engine: Any = None,
) -> int:
    """Entry point for ``loopos fusion-router <action>``."""

    router = router or build_default_router()
    store = store or build_default_store()

    if action == "plan":
        if not task_arg:
            print("fusion-router plan requires TASK (path or JSON).", file=sys.stderr)
            return 1
        plan = cli_plan(task_arg, router=router, json_output=json_output)
        # Persist the plan so ``status`` can return it.
        store.save_plan(plan)
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
        plan = (
            cli_dry_run(task_arg, router=router, json_output=json_output)
            if dry_run else cli_plan(task_arg, router=router, json_output=json_output)
        )
        store.save_plan(plan)
        return 0
    if action == "escalate":
        if not run_id:
            print("fusion-router escalate requires --run-id.", file=sys.stderr)
            return 1
        plan = cli_escalate(
            run_id=run_id, reason=reason,
            router=router, json_output=json_output,
        )
        store.save_plan(plan)
        return 0
    if action == "status":
        if not fusion_id:
            print("fusion-router status requires FUSION_ID.", file=sys.stderr)
            return 1
        cli_status(fusion_id, store=store, json_output=json_output)
        return 0
    if action == "list":
        cli_list(store=store, json_output=json_output)
        return 0
    if action == "route":
        # Phase 7: opt-in routing through the kernel.
        if not fusion_id:
            print("fusion-router route requires --fusion-id.", file=sys.stderr)
            return 1
        from loopos.fusion_router.models import FusionPlan
        routed_plan: FusionPlan | None = store.load_plan(fusion_id)
        if routed_plan is None:
            print(
                f"fusion-router route: no persisted plan for {fusion_id!r}; "
                "run `fusion-router plan <task>` first.",
                file=sys.stderr,
            )
            return 1
        runner = FusionRunner(kernel_engine=kernel_engine, store=store)
        result = runner.run(
            routed_plan,
            execution_enabled=kernel_engine is not None,
        )
        if json_output:
            from loopos.fusion_router.cli import emit_json
            emit_json(result.to_dict())
        else:
            sys.stdout.write(
                f"fusion_id: {result.fusion_id}\n"
                f"mode:      {result.mode}\n"
                f"status:    {result.status}\n"
                f"records:   {len(result.records)}\n"
                f"results:   {len(result.results)}\n"
                f"fallback:  {result.fallback_reason or '(none)'}\n"
            )
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
    "build_default_runner",
    "build_default_store",
    "cli_list",
    "cli_status",
    "fusion_router_command",
]