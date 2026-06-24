"""LoopOS CLI/FLI entry point."""

from __future__ import annotations

import importlib.util
import sys
from typing import Any

# Keep release/source commands from writing bytecode for modules imported below.
sys.dont_write_bytecode = True

from loopos.cli.commands import (  # noqa: E402
    ail_command as ail_command,
    code_command as code_command,
    config_command as config_command,
    db_command as db_command,
    distill_command as distill_command,
    files_command as files_command,
    fusion_command as fusion_command,
    fusion_router_command as fusion_router_command,
    gateway_command as gateway_command,
    goal_command as goal_command,
    imagine_command as imagine_command,
    kernel_command as kernel_command,
    lail_encode_command as lail_encode_command,
    loop_deliver_command as loop_deliver_command,
    loop_optimize_command as loop_optimize_command,
    loop_repair_command as loop_repair_command,
    loop_review_command as loop_review_command,
    loop_run_command as loop_run_command,
    loop_status_command as loop_status_command,
    mad_dog_command as mad_dog_command,
    memory_command as memory_command,
    memory_compile_command as memory_compile_command,
    mode_command as mode_command,
    models_command as models_command,
    parse_goal_options as _parse_goal_options,  # noqa: F401 - compatibility export
    policy_command as policy_command,
    profile_command as profile_command,
    providers_command as providers_command,
    registry_command as registry_command,
    release_command as release_command,
    review_command as review_command,
    skills_command as skills_command,
    search_command as search_command,
    index_command as index_command,
    tasks_command as tasks_command,
    triggers_command as triggers_command,
    worktrees_command as worktrees_command,
)

from loopos.cli.context import data_paths  # noqa: E402
from loopos.cli.fallback import fallback_main  # noqa: E402
from loopos.cli.commands.runtime import (  # noqa: E402
    history_command as history_command,
    replay_command as replay_command,
    repl_command as repl_command,
    resume_command as resume_command,
    run_command as run_command,
    status_command as status_command,
    tools_command as tools_command,
    trace_command as trace_command,
)
from loopos.cli.help_text import COMMAND_HELP as _COMMAND_HELP  # noqa: E402
from loopos.cli.renderers import render_run as _render_run  # noqa: E402, F401
from loopos.cli.renderers import render_state as _render_state  # noqa: E402, F401


# Probe optional CLI dependencies up front so the rest of the module
# sees a single, type-narrowable binding for ``typer_mod`` and
# ``ConsoleCls``.  The previous ``try/except import`` shape made
# mypy report ``no-redef`` for the re-binding in the ``except`` arm
# and was easy to misuse (callers had to assume ``Any`` everywhere).
# ``importlib.util.find_spec`` keeps the bootstrap path optional
# without introducing a second definition; the explicit ``Any``
# annotations keep call sites (``typer_mod.Option(...)`` etc.)
# narrowable without the helper having to assert non-None on every
# branch.
typer_mod: Any
ConsoleCls: Any

if (
    importlib.util.find_spec("typer") is not None
    and importlib.util.find_spec("rich") is not None
):
    import typer as typer_mod
    from rich.console import Console as ConsoleCls

    _HAS_TUI = True
else:  # pragma: no cover - exercised in dependency-light environments.
    typer_mod = None
    ConsoleCls = None
    _HAS_TUI = False

if _HAS_TUI:
    app: Any = typer_mod.Typer(help="LoopOS terminal-native AI-ISA runtime.")
    console: Any = ConsoleCls()
else:
    app = None
    console = None


_paths = data_paths

if _HAS_TUI:

    @app.command("run")
    def _typer_run(
        goal: str,
        max_steps: int = typer_mod.Option(20, "--max-steps"),
        dry_run: bool = typer_mod.Option(False, "--dry-run"),
        yes: bool = typer_mod.Option(False, "--yes"),
        verbose: bool = typer_mod.Option(False, "--verbose"),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        workspace: str = typer_mod.Option(".", "--workspace"),
        mode: str = typer_mod.Option("guarded", "--mode"),
        show_ail: bool = typer_mod.Option(False, "--show-ail"),
        show_policy: bool = typer_mod.Option(False, "--show-policy"),
        json_output: bool = typer_mod.Option(False, "--json"),
        goal_option: str | None = typer_mod.Option(None, "--goal-option"),
        confirm_goal: bool = typer_mod.Option(False, "--confirm-goal"),
        memory: str = typer_mod.Option("on", "--memory"),
        propose_memory: bool = typer_mod.Option(False, "--propose-memory"),
        llm_provider: str = typer_mod.Option("mock", "--llm-provider"),
    ) -> None:
        raise typer_mod.Exit(
            run_command(
                goal,
                max_steps=max_steps,
                dry_run=dry_run,
                yes=yes,
                verbose=verbose,
                data_dir=data_dir,
                memory=memory,
                propose_memory=propose_memory,
                llm_provider=llm_provider,
                workspace=workspace,
                mode=mode,
                show_ail=show_ail,
                show_policy=show_policy,
                json_output=json_output,
                goal_option=goal_option,
                confirm_goal=confirm_goal,
            )
        )

    @app.command("resume")
    def _typer_resume(
        run_id: str,
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        approve: bool = typer_mod.Option(False, "--approve"),
        deny: bool = typer_mod.Option(False, "--deny"),
        verbose: bool = typer_mod.Option(False, "--verbose"),
        json_output: bool = typer_mod.Option(False, "--json"),
    ) -> None:
        raise typer_mod.Exit(
            resume_command(
                run_id,
                data_dir=data_dir,
                approve=approve,
                deny=deny,
                verbose=verbose,
                json_output=json_output,
            )
        )

    @app.command("status")
    def _typer_status(
        run_id: str,
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        verbose: bool = typer_mod.Option(False, "--verbose"),
    ) -> None:
        raise typer_mod.Exit(status_command(run_id, data_dir=data_dir, verbose=verbose))

    @app.command("history")
    def _typer_history(
        run_id: str,
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
    ) -> None:
        raise typer_mod.Exit(history_command(run_id, data_dir=data_dir))

    @app.command("skills")
    def _typer_skills(
        action: str = typer_mod.Argument("list"),
        arg: str | None = typer_mod.Argument(None),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
    ) -> None:
        raise typer_mod.Exit(skills_command(action, arg, data_dir=data_dir))

    @app.command("trace")
    def _typer_trace(
        run_id: str,
        value: str | None = typer_mod.Argument(None),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        show_ail: bool = typer_mod.Option(False, "--show-ail"),
        show_policy: bool = typer_mod.Option(False, "--show-policy"),
        json_output: bool = typer_mod.Option(False, "--json"),
    ) -> None:
        raise typer_mod.Exit(
            trace_command(
                run_id,
                value,
                data_dir=data_dir,
                show_ail=show_ail,
                show_policy=show_policy,
                json_output=json_output,
            )
        )

    @app.command("step")
    def _typer_step(
        action: str,
        run_id: str,
        step: int,
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        json_output: bool = typer_mod.Option(False, "--json"),
    ) -> None:
        if action != "replay":
            console.print(f"Unknown step action: {action}", style="red")
            raise typer_mod.Exit(1)
        raise typer_mod.Exit(
            replay_command(run_id, step, data_dir=data_dir, json_output=json_output)
        )

    @app.command("tools")
    def _typer_tools(
        action: str = typer_mod.Argument("list"),
        workspace: str = typer_mod.Option(".", "--workspace"),
        json_output: bool = typer_mod.Option(False, "--json"),
    ) -> None:
        raise typer_mod.Exit(
            tools_command(action, workspace=workspace, json_output=json_output)
        )

    @app.command("goal")
    def _typer_goal(
        action: str,
        raw_goal: str,
        option: str | None = typer_mod.Option(None, "--option"),
        confirmed: bool = typer_mod.Option(False, "--confirm"),
        json_output: bool = typer_mod.Option(False, "--json"),
    ) -> None:
        raise typer_mod.Exit(
            goal_command(
                action,
                raw_goal,
                option=option,
                confirmed=confirmed,
                json_output=json_output,
            )
        )

    @app.command("db")
    def _typer_db(
        action: str = typer_mod.Argument("detect"),
        arg: str | None = typer_mod.Argument(None),
        cmd: str | None = typer_mod.Option(None, "--cmd"),
        target: str | None = typer_mod.Option(None, "--target"),
        source: str | None = typer_mod.Option(None, "--source"),
        backup_id: str | None = typer_mod.Option(None, "--backup-id"),
        migration: str | None = typer_mod.Option(None, "--migration"),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        workspace: str = typer_mod.Option(".", "--workspace"),
        yes: bool = typer_mod.Option(False, "--yes"),
        json_output: bool = typer_mod.Option(False, "--json"),
        human_output: bool = typer_mod.Option(False, "--human"),
    ) -> None:
        raise typer_mod.Exit(
            db_command(
                action,
                arg,
                cmd=cmd,
                target=target,
                source=source,
                backup_id=backup_id,
                migration=migration,
                data_dir=data_dir,
                workspace=workspace,
                yes=yes,
                json_output=json_output,
                human_output=human_output,
            )
        )

    @app.command("tasks")
    def _typer_tasks(
        action: str = typer_mod.Argument("list"),
        arg: str | None = typer_mod.Argument(None),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        quick_win: bool = typer_mod.Option(False, "--quick-win"),
        json_output: bool = typer_mod.Option(False, "--json"),
        goal: str | None = typer_mod.Option(None, "--goal"),
        task_type: str = typer_mod.Option("coordination", "--type"),
        text: str | None = typer_mod.Option(None, "--text"),
        content: str | None = typer_mod.Option(None, "--content"),
        title: str | None = typer_mod.Option(None, "--title"),
        requires_worktree: bool = typer_mod.Option(False, "--requires-worktree"),
        ready: bool = typer_mod.Option(False, "--ready"),
    ) -> None:
        raise typer_mod.Exit(
            tasks_command(
                action,
                arg,
                data_dir=data_dir,
                quick_win=quick_win,
                json_output=json_output,
                goal=goal,
                task_type=task_type,
                text=text,
                content=content,
                title=title,
                requires_worktree=requires_worktree,
                ready=ready,
            )
        )

    @app.command("index")
    def _typer_index(
        action: str = typer_mod.Argument("status"),
        workspace: str = typer_mod.Option(".", "--workspace"),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
    ) -> None:
        raise typer_mod.Exit(index_command(action, workspace=workspace, data_dir=data_dir))

    @app.command("search")
    def _typer_search(
        query: str,
        value: str | None = typer_mod.Argument(None),
        workspace: str = typer_mod.Option(".", "--workspace"),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        limit: int = typer_mod.Option(20, "--limit"),
    ) -> None:
        raise typer_mod.Exit(
            search_command(
                query, value, workspace=workspace, data_dir=data_dir, limit=limit
            )
        )

    @app.command("files")
    def _typer_files(
        action: str,
        query: str,
        workspace: str = typer_mod.Option(".", "--workspace"),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
    ) -> None:
        raise typer_mod.Exit(
            files_command(action, query, workspace=workspace, data_dir=data_dir)
        )

    @app.command("mode")
    def _typer_mode(
        action: str = typer_mod.Argument("status"),
        value: str | None = typer_mod.Argument(None),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        private_data: bool = typer_mod.Option(False, "--private-data"),
        sanitized: bool = typer_mod.Option(False, "--sanitized"),
        cloud_consent: bool = typer_mod.Option(False, "--cloud-consent"),
    ) -> None:
        raise typer_mod.Exit(
            mode_command(
                action,
                value,
                data_dir=data_dir,
                private_data=private_data,
                sanitized=sanitized,
                cloud_consent=cloud_consent,
            )
        )

    @app.command("registry")
    def _typer_registry(
        action: str = typer_mod.Argument("list"),
        value: str | None = typer_mod.Argument(None),
        plugin_type: str | None = typer_mod.Option(None, "--type"),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
    ) -> None:
        raise typer_mod.Exit(
            registry_command(
                action,
                value,
                plugin_type=plugin_type,
                data_dir=data_dir,
            )
        )

    @app.command("triggers")
    def _typer_triggers(
        action: str = typer_mod.Argument("list"),
        trigger_id: str | None = typer_mod.Argument(None),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
    ) -> None:
        raise typer_mod.Exit(triggers_command(action, trigger_id, data_dir=data_dir))

    @app.command("worktrees")
    def _typer_worktrees(
        action: str = typer_mod.Argument("list"),
        task_id: str | None = typer_mod.Argument(None),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        workspace: str = typer_mod.Option(".", "--workspace"),
        dry_run: bool = typer_mod.Option(True, "--dry-run/--execute"),
        yes: bool = typer_mod.Option(False, "--yes"),
    ) -> None:
        raise typer_mod.Exit(
            worktrees_command(
                action,
                task_id,
                data_dir=data_dir,
                workspace=workspace,
                dry_run=dry_run,
                yes=yes,
            )
        )

    @app.command("review")
    def _typer_review(
        action: str = typer_mod.Argument("list"),
        task_id: str | None = typer_mod.Argument(None),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        producer: str = typer_mod.Option("producer", "--producer"),
        verifier: str = typer_mod.Option("verifier", "--verifier"),
        reviewer: str = typer_mod.Option("reviewer", "--reviewer"),
        actor: str | None = typer_mod.Option(None, "--actor"),
        note: str | None = typer_mod.Option(None, "--note"),
        run_id: str | None = typer_mod.Option(None, "--run-id"),
        high_risk: bool = typer_mod.Option(False, "--high-risk"),
        maintainability_blocked: bool = typer_mod.Option(False, "--maintainability-blocked"),
        diff_file: str | None = typer_mod.Option(None, "--diff"),
        human_output: bool = typer_mod.Option(False, "--human"),
    ) -> None:
        raise typer_mod.Exit(
            review_command(
                action,
                task_id,
                data_dir=data_dir,
                producer=producer,
                verifier=verifier,
                reviewer=reviewer,
                actor=actor,
                note=note,
                run_id=run_id,
                high_risk=high_risk,
                maintainability_blocked=maintainability_blocked,
                diff_file=diff_file,
                human_output=human_output,
            )
        )

    @app.command("providers")
    def _typer_providers(
        action: str = typer_mod.Argument("list"),
        value: str | None = typer_mod.Argument(None),
        json_output: bool = typer_mod.Option(False, "--json"),
    ) -> None:
        raise typer_mod.Exit(providers_command(action, value, json_output=json_output))

    @app.command("models")
    def _typer_models(
        action: str = typer_mod.Argument("route"),
        task: str = typer_mod.Option("general", "--task"),
        input_kind: str | None = typer_mod.Option(None, "--input"),
        secret: bool = typer_mod.Option(False, "--secret"),
    ) -> None:
        raise typer_mod.Exit(
            models_command(action, task=task, input_kind=input_kind, secret=secret)
        )

    @app.command("gateway")
    def _typer_gateway(
        action: str = typer_mod.Argument("simulate"),
        channel: str = typer_mod.Argument("telegram"),
        text: str = typer_mod.Argument("hello"),
        user_id: str = typer_mod.Option("user", "--user-id"),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        run_id: str | None = typer_mod.Option(None, "--run-id"),
        risk: str = typer_mod.Option("medium", "--risk"),
        reason_code: str | None = typer_mod.Option(None, "--reason-code"),
        approve: bool = typer_mod.Option(False, "--approve"),
        deny: bool = typer_mod.Option(False, "--deny"),
    ) -> None:
        raise typer_mod.Exit(
            gateway_command(
                action,
                channel,
                text,
                user_id=user_id,
                data_dir=data_dir,
                run_id=run_id,
                risk=risk,
                reason_code=reason_code,
                approve=approve,
                deny=deny,
            )
        )

    @app.command("memory")
    def _typer_memory(
        action: str = typer_mod.Argument("list"),
        arg: str | None = typer_mod.Argument(None),
        from_run: str | None = typer_mod.Option(None, "--from-run"),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        verbose: bool = typer_mod.Option(False, "--verbose"),
        role: str | None = typer_mod.Option(None, "--role"),
        # v0.4.0 closeout: route ``memory compile --items`` to the
        # closeout ``memory_compile_command``. All other actions go
        # to the v0.1 ``memory_command`` (which still supports
        # ``list`` / ``search`` / ``propose`` / ``reindex`` /
        # ``review`` / ``accept`` / ``reject`` / ``compile``
        # (no-items) / ``failures`` / ``decisions``).
        items: str | None = typer_mod.Option(None, "--items"),
        items_file: str | None = typer_mod.Option(None, "--items-file"),
        goal_summary: str = typer_mod.Option("", "--goal"),
        current_gap: str = typer_mod.Option("", "--gap"),
        token_budget: int = typer_mod.Option(900, "--token-budget"),
        run_id: str | None = typer_mod.Option(None, "--run-id"),
        iteration_index: int = typer_mod.Option(0, "--iteration"),
        json_output: bool = typer_mod.Option(True, "--json/--human"),
    ) -> None:
        if action == "compile" and (items is not None or items_file is not None):
            raise typer_mod.Exit(
                memory_compile_command(
                    items=items or "[]",
                    items_file=items_file,
                    target_role=role or "planner",
                    goal_summary=goal_summary,
                    current_gap=current_gap,
                    token_budget=token_budget,
                    run_id=run_id,
                    iteration_index=iteration_index,
                    json_output=json_output,
                )
            )
        raise typer_mod.Exit(
            memory_command(
                action,
                arg,
                from_run=from_run,
                data_dir=data_dir,
                verbose=verbose,
                role=role,
            )
        )

    @app.command("profile")
    def _typer_profile(
        action: str = typer_mod.Argument("show"),
        key: str | None = typer_mod.Argument(None),
        value: str | None = typer_mod.Argument(None),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
    ) -> None:
        raise typer_mod.Exit(profile_command(action, key, value, data_dir=data_dir))

    @app.command("config")
    def _typer_config(data_dir: str = typer_mod.Option(".loopos", "--data-dir")) -> None:
        raise typer_mod.Exit(config_command(data_dir=data_dir))

    @app.command("policy")
    def _typer_policy(
        action: str = typer_mod.Argument("list"),
        policy_id: str | None = typer_mod.Argument(None),
        scope: str | None = typer_mod.Option(None, "--scope"),
        input_json: str | None = typer_mod.Option(None, "--input"),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        verbose: bool = typer_mod.Option(False, "--verbose"),
        cmd: str | None = typer_mod.Option(None, "--cmd"),
        human_output: bool = typer_mod.Option(False, "--human"),
    ) -> None:
        raise typer_mod.Exit(
            policy_command(
                action,
                policy_id,
                scope=scope,
                input_json=input_json,
                data_dir=data_dir,
                verbose=verbose,
                cmd=cmd,
                human_output=human_output,
            )
        )

    @app.command("ail")
    def _typer_ail(
        action: str = typer_mod.Argument("validate"),
        file: str | None = typer_mod.Argument(None),
        verbose: bool = typer_mod.Option(False, "--verbose"),
    ) -> None:
        raise typer_mod.Exit(ail_command(action, file, verbose=verbose))

    @app.command("lail")
    # v0.4.0 — LAIL encode is registered at the bottom of this block
    # in the closeout section. The v0.1 stub `lail_command` was
    # removed because it was never implemented in the v0.1 tree.

    @app.command("code")
    def _typer_code(
        ctx: typer_mod.Context,
        action: str = typer_mod.Argument("summary"),
        diff_file: str | None = typer_mod.Option(None, "--diff"),
        use_json: bool = typer_mod.Option(False, "--json"),
    ) -> None:
        args: list[str] = [action]
        if diff_file is not None:
            args.extend(["--diff", diff_file])
        if use_json:
            args.append("--json")
        code_command(args)
        raise typer_mod.Exit(0)

    @app.command("fusion")
    def _typer_fusion(
        action: str = typer_mod.Argument("plan"),
        prompt: str | None = typer_mod.Argument(None),
        panel: str = typer_mod.Option("balanced", "--panel"),
        task_type: str = typer_mod.Option("unknown", "--task-type"),
        risk: str = typer_mod.Option("medium", "--risk"),
        privacy: str = typer_mod.Option("hybrid", "--privacy"),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        json_output: bool = typer_mod.Option(False, "--json"),
    ) -> None:
        raise typer_mod.Exit(
            fusion_command(
                action,
                prompt,
                panel=panel,
                task_type=task_type,
                risk=risk,
                privacy=privacy,
                data_dir=data_dir,
                json_output=json_output,
            )
        )

    @app.command(
        "fusion-router",
        help=_COMMAND_HELP["fusion-router"].short,
        epilog=_COMMAND_HELP["fusion-router"].long,
    )
    def _typer_fusion_router(
        action: str = typer_mod.Option("plan", "--action"),
        task: str | None = typer_mod.Option(None, "--task"),
        run_id: str | None = typer_mod.Option(None, "--run-id"),
        reason: str = typer_mod.Option("repeated_failure", "--reason"),
        fusion_id: str | None = typer_mod.Option(None, "--fusion-id"),
        dry_run: bool = typer_mod.Option(False, "--dry-run"),
        json_output: bool = typer_mod.Option(True, "--json/--human"),
    ) -> None:
        # ``--task`` is meaningful only for plan / explain / run.
        # For escalate / status / list / route the wrapper must not
        # forward ``task`` (the underlying command does not need it,
        # and forwarding can re-trigger ``Path(task_arg).exists()`` if
        # ``task`` was a long inline-JSON payload).
        task_arg = task if action in ("plan", "explain", "run") else None
        raise typer_mod.Exit(
            fusion_router_command(
                action=action,
                task_arg=task_arg,
                run_id=run_id,
                reason=reason,
                fusion_id=fusion_id,
                dry_run=dry_run,
                json_output=json_output,
            )
        )

    @app.command(
        "mad-dog",
        help=_COMMAND_HELP["mad-dog"].short,
        epilog=_COMMAND_HELP["mad-dog"].long,
    )
    def _typer_mad_dog(
        action: str = typer_mod.Option("plan", "--action"),
        task: str | None = typer_mod.Option(None, "--task"),
        run_id: str | None = typer_mod.Option(None, "--run-id"),
        reason: str = typer_mod.Option("explicit_user_request", "--reason"),
        severity: str = typer_mod.Option("critical", "--severity"),
        fusion_id: str | None = typer_mod.Option(None, "--fusion-id"),
        json_output: bool = typer_mod.Option(True, "--json/--human"),
    ) -> None:
        # See note in ``_typer_fusion_router``: ``--task`` is meaningful
        # only for plan / explain. For escalate / status / list / route
        # we deliberately drop ``task`` so the wrapper never re-parses
        # a long inline-JSON payload as a filesystem path.
        task_arg = task if action in ("plan", "explain") else None
        raise typer_mod.Exit(
            mad_dog_command(
                action=action,
                task_arg=task_arg,
                run_id=run_id,
                reason=reason,
                severity=severity,
                fusion_id=fusion_id,
                json_output=json_output,
            )
        )

    @app.command("distill")
    def _typer_distill(
        action: str = typer_mod.Argument("inspect"),
        target: str | None = typer_mod.Argument(None),
        json_output: bool = typer_mod.Option(False, "--json"),
    ) -> None:
        raise typer_mod.Exit(
            distill_command(action, target, json_output=json_output)
        )

    @app.command("kernel")
    def _typer_kernel(
        action: str = typer_mod.Argument("inspect"),
        run_id: str | None = typer_mod.Argument(None),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        json_output: bool = typer_mod.Option(False, "--json"),
    ) -> None:
        raise typer_mod.Exit(
            kernel_command(
                action,
                run_id,
                data_dir=data_dir,
                json_output=json_output,
            )
        )

    # v0.3 commands (extracted to loopos/cli/typer_v0_3.py)
    from loopos.cli.typer_v0_3 import register_v0_3_commands
    register_v0_3_commands(app, typer_mod)

    # v0.4.0 — Loop Engineering commands (closeout: cross-process)
    @app.command("loop")
    def _typer_loop(
        action: str = typer_mod.Argument("run"),
        goal: str | None = typer_mod.Argument(None),
        max_iterations: int = typer_mod.Option(3, "--max-iterations"),
        dry_run: bool = typer_mod.Option(True, "--dry-run/--no-dry-run"),
        mad_dog: bool = typer_mod.Option(False, "--mad-dog"),
        json_output: bool = typer_mod.Option(True, "--json/--human"),
        run_id: str | None = typer_mod.Option(None, "--run-id"),
        latest: bool = typer_mod.Option(False, "--latest"),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
    ) -> None:
        rid = "latest" if latest else run_id
        if action == "run":
            if not goal:
                raise typer_mod.BadParameter("goal is required for `loop run`")
            raise typer_mod.Exit(
                loop_run_command(
                    goal=goal,
                    max_iterations=max_iterations,
                    dry_run=dry_run,
                    json_output=json_output,
                    run_id=rid,
                    data_dir=data_dir,
                )
            )
        if action == "status":
            raise typer_mod.Exit(
                loop_status_command(
                    run_id=rid, json_output=json_output, data_dir=data_dir,
                )
            )
        if action == "review":
            raise typer_mod.Exit(
                loop_review_command(
                    mad_dog=mad_dog, json_output=json_output,
                    run_id=rid, data_dir=data_dir,
                )
            )
        if action == "repair":
            raise typer_mod.Exit(
                loop_repair_command(
                    json_output=json_output, run_id=rid, data_dir=data_dir,
                )
            )
        if action == "optimize":
            raise typer_mod.Exit(
                loop_optimize_command(
                    json_output=json_output, run_id=rid, data_dir=data_dir,
                )
            )
        if action == "deliver":
            raise typer_mod.Exit(
                loop_deliver_command(
                    run_id=rid, json_output=json_output, data_dir=data_dir,
                )
            )
        raise typer_mod.BadParameter(f"unknown loop action: {action}")

    @app.command("imagine")
    def _typer_imagine(
        prompt: str,
        mode: str = typer_mod.Option("brainstorm", "--mode"),
        max_candidates: int = typer_mod.Option(3, "--max-candidates"),
        json_output: bool = typer_mod.Option(True, "--json/--human"),
    ) -> None:
        raise typer_mod.Exit(
            imagine_command(
                prompt=prompt,
                mode=mode,
                max_candidates=max_candidates,
                json_output=json_output,
            )
        )

    @app.command("lail")
    def _typer_lail(
        action: str = typer_mod.Argument("encode"),
        kind: str = typer_mod.Option("iteration_started", "--kind"),
        run_id: str = typer_mod.Option("run_local", "--run-id"),
        iteration_index: int = typer_mod.Option(0, "--iteration"),
        trace_id: str | None = typer_mod.Option(None, "--trace-id"),
        payload: str | None = typer_mod.Option(None, "--payload"),
        json_output: bool = typer_mod.Option(True, "--json/--human"),
    ) -> None:
        if action == "encode":
            raise typer_mod.Exit(
                lail_encode_command(
                    kind=kind,
                    run_id=run_id,
                    iteration_index=iteration_index,
                    trace_id=trace_id,
                    payload=payload,
                    json_output=json_output,
                )
            )
        raise typer_mod.BadParameter(f"unknown lail action: {action}")

    @app.command("release")
    def _typer_release(
        action: str = typer_mod.Argument("check"),
        version: str = typer_mod.Option("0.1.0", "--version"),
        source: str = typer_mod.Option(".", "--source", "--workspace"),
        output: str = typer_mod.Option("dist", "--output"),
        no_zip: bool = typer_mod.Option(False, "--no-zip"),
        strict: bool = typer_mod.Option(False, "--strict"),
        ignore_local_only: bool = typer_mod.Option(False, "--ignore-local-only"),
        strict_source: bool = typer_mod.Option(False, "--strict-source"),
        deep: bool = typer_mod.Option(False, "--deep"),
        timeout_per_check: int = typer_mod.Option(60, "--timeout-per-check", min=1),
        global_timeout: int = typer_mod.Option(300, "--global-timeout", min=1),
        json_output: bool = typer_mod.Option(False, "--json"),
        target: str = typer_mod.Option("founding-preview", "--target"),
    ) -> None:
        raise typer_mod.Exit(
            release_command(
                action,
                version=version,
                source=source,
                output=output,
                no_zip=no_zip,
                strict=strict,
                ignore_local_only=ignore_local_only,
                strict_source=strict_source,
                deep=deep,
                timeout_per_check=timeout_per_check,
                global_timeout=global_timeout,
                json_output=json_output,
                target=target,
            )
        )


def main(argv: list[str] | None = None) -> int:
    _configure_utf8_streams()
    if _HAS_TUI and argv is None:
        if len(sys.argv) == 1 and sys.stdin.isatty():
            return repl_command()
        app()
        return 0
    return fallback_main(argv)


def _configure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8")
            except (AttributeError, OSError):
                pass


if __name__ == "__main__":
    raise SystemExit(main())
