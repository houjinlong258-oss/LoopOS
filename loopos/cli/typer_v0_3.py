"""LoopOS v0.3 Typer command bindings.

The seven v0.3 Typer bindings (``workbench``, ``adapters``,
``providers-runtime``, ``model-call``, ``opengod``, ``session``,
``readiness``) used to live inline in ``loopos/cli/app.py``,
adding ~140 lines to a file that already exceeded the 300-LOC
anti-bloat soft cap. The P1-4 hardening pass extracts them
into this module so ``app.py`` shrinks without changing the
user-facing CLI surface.

Design:

* The :func:`register_v0_3_commands` function takes a Typer
  ``app`` and the optional ``typer`` module (so the caller can
  wire the same module under Typer and under the argparse
  fallback). It registers the seven v0.3 commands on the app.
* The v0.3 commands delegate to the corresponding pure
  command functions in :mod:`loopos.cli.commands` (the same
  functions used by the argparse fallback). This keeps the
  Typer path and the argparse path on a single source of
  truth for argument parsing, validation, and exit codes.
* The argparse fallback in :mod:`loopos.cli.fallback` is
  unchanged; it routes the same command names to the same
  underlying functions.

No CLI behavior change. The user-facing command surface is
identical: ``loopos workbench ...``, ``loopos adapters ...``,
``loopos providers-runtime ...``, ``loopos model-call ...``,
``loopos opengod ...``, ``loopos session ...``, ``loopos
readiness check``.
"""

from __future__ import annotations

from typing import Any

from loopos.cli.commands import (
    adapters_command,
    model_call_command,
    opengod_command,
    providers_runtime_command,
    readiness_command,
    session_command,
    workbench_command,
)


def register_v0_3_commands(app: Any, typer_mod: Any) -> None:
    """Register the seven v0.3 Typer commands on ``app``.

    The caller is responsible for ensuring ``app`` is a Typer
    app and ``typer_mod`` is the imported ``typer`` module.
    The two arguments are kept separate so the caller can pass
    ``None`` for ``app`` in dependency-light environments
    (the registration is then a no-op).
    """
    if app is None or typer_mod is None:
        return

    @app.command("workbench")
    def _typer_workbench(
        goal_path: str | None = typer_mod.Argument(None),
        adapter: str = typer_mod.Option("mock", "--adapter"),
        model: str = typer_mod.Option("mock-model", "--model"),
        provider: str = typer_mod.Option("mock", "--provider"),
        mode: str = typer_mod.Option("single", "--mode"),
        budget_usd: float = typer_mod.Option(0.0, "--budget-usd"),
        mad_dog: bool = typer_mod.Option(False, "--mad-dog"),
        allow_live_provider: bool = typer_mod.Option(
            False, "--allow-live-provider"
        ),
        dry_run: bool = typer_mod.Option(True, "--dry-run/--no-dry-run"),
        watch: bool = typer_mod.Option(False, "--watch"),
        json_output: bool = typer_mod.Option(False, "--json"),
        project: str = typer_mod.Option("", "--project"),
    ) -> None:
        raise typer_mod.Exit(
            workbench_command(
                goal_path,
                adapter=adapter,
                model=model,
                provider=provider,
                mode=mode,
                budget_usd=budget_usd,
                mad_dog=mad_dog,
                allow_live_provider=allow_live_provider,
                dry_run=dry_run,
                watch=watch,
                json_output=json_output,
                project=project,
            )
        )

    @app.command("adapters")
    def _typer_adapters(
        action: str = typer_mod.Argument("list"),
        value: str | None = typer_mod.Argument(None),
        json_output: bool = typer_mod.Option(False, "--json"),
    ) -> None:
        raise typer_mod.Exit(
            adapters_command(action, value, json_output=json_output)
        )

    @app.command("providers-runtime")
    def _typer_providers_runtime(
        action: str = typer_mod.Argument("list"),
        value: str | None = typer_mod.Argument(None),
        model: str = typer_mod.Option("mock-model", "--model"),
        dry_run: bool = typer_mod.Option(True, "--dry-run"),
        json_output: bool = typer_mod.Option(False, "--json"),
    ) -> None:
        raise typer_mod.Exit(
            providers_runtime_command(
                action, value, model=model, dry_run=dry_run, json_output=json_output
            )
        )

    @app.command("model-call")
    def _typer_model_call(
        prompt_path: str,
        provider: str = typer_mod.Option("mock", "--provider"),
        model: str = typer_mod.Option("mock-model", "--model"),
        dry_run: bool = typer_mod.Option(True, "--dry-run/--no-dry-run"),
        allow_live_provider: bool = typer_mod.Option(
            False, "--allow-live-provider"
        ),
        budget_usd: float = typer_mod.Option(0.0, "--budget-usd"),
        confirm: bool = typer_mod.Option(False, "--confirm"),
        json_output: bool = typer_mod.Option(True, "--json"),
    ) -> None:
        raise typer_mod.Exit(
            model_call_command(
                prompt_path,
                provider=provider,
                model=model,
                dry_run=dry_run,
                allow_live_provider=allow_live_provider,
                budget_usd=budget_usd,
                confirm=confirm,
                json_output=json_output,
            )
        )

    @app.command("opengod")
    def _typer_opengod(
        goal_id: str = typer_mod.Argument("goal_demo"),
        goal_title: str = typer_mod.Option("", "--goal-title"),
        goal_risk: str = typer_mod.Option("medium", "--goal-risk"),
        fusion_mode: str = typer_mod.Option("single", "--fusion-mode"),
        fusion_score: int = typer_mod.Option(0, "--fusion-score"),
        hard_fail_count: int = typer_mod.Option(0, "--hard-fail-count"),
        readiness_status: str = typer_mod.Option(
            "unknown", "--readiness-status"
        ),
        adapter_id: str = typer_mod.Option("", "--adapter-id"),
        live_provider_calls: bool = typer_mod.Option(
            False, "--live-provider-calls"
        ),
        budget_used_usd: float = typer_mod.Option(0.0, "--budget-used-usd"),
        budget_max_usd: float = typer_mod.Option(0.0, "--budget-max-usd"),
        max_budget_usd: float = typer_mod.Option(1.0, "--max-budget-usd"),
        reserve_usd: float = typer_mod.Option(0.10, "--reserve-usd"),
        json_output: bool = typer_mod.Option(True, "--json"),
    ) -> None:
        raise typer_mod.Exit(
            opengod_command(
                goal_id,
                goal_title=goal_title,
                goal_risk=goal_risk,
                fusion_mode=fusion_mode,
                fusion_score=fusion_score,
                hard_fail_count=hard_fail_count,
                readiness_status=readiness_status,
                adapter_id=adapter_id,
                live_provider_calls=live_provider_calls,
                budget_used_usd=budget_used_usd,
                budget_max_usd=budget_max_usd,
                max_budget_usd=max_budget_usd,
                reserve_usd=reserve_usd,
                json_output=json_output,
            )
        )

    @app.command("session")
    def _typer_session(
        action: str = typer_mod.Argument("list"),
        session_id: str | None = typer_mod.Argument(None),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        json_output: bool = typer_mod.Option(False, "--json"),
    ) -> None:
        raise typer_mod.Exit(
            session_command(
                action, session_id, data_dir=data_dir, json_output=json_output
            )
        )

    @app.command("readiness")
    def _typer_readiness(
        action: str = typer_mod.Argument("check"),
        json_output: bool = typer_mod.Option(True, "--json"),
    ) -> None:
        raise typer_mod.Exit(
            readiness_command(action, json_output=json_output)
        )


__all__ = ["register_v0_3_commands"]