"""LoopOS CLI/FLI entry point."""

from __future__ import annotations

import sys
from typing import Any

from loopos.cli.commands import (
    ail_command as ail_command,
    config_command as config_command,
    db_command as db_command,
    gateway_command as gateway_command,
    goal_command as goal_command,
    memory_command as memory_command,
    models_command as models_command,
    parse_goal_options as _parse_goal_options,  # noqa: F401 - compatibility export
    policy_command as policy_command,
    profile_command as profile_command,
    providers_command as providers_command,
    review_command as review_command,
    skills_command as skills_command,
    tasks_command as tasks_command,
    triggers_command as triggers_command,
    worktrees_command as worktrees_command,
)
from loopos.cli.context import data_paths
from loopos.cli.fallback import fallback_main
from loopos.cli.commands.runtime import (
    history_command as history_command,
    replay_command as replay_command,
    repl_command as repl_command,
    resume_command as resume_command,
    run_command as run_command,
    status_command as status_command,
    tools_command as tools_command,
    trace_command as trace_command,
)
from loopos.cli.renderers import render_run as _render_run  # noqa: F401
from loopos.cli.renderers import render_state as _render_state  # noqa: F401


typer_mod: Any
ConsoleCls: Any

try:  # Optional for local bootstrapping.
    import typer as typer_mod
    from rich.console import Console as ConsoleCls

    _HAS_TUI = True
except Exception:  # pragma: no cover - exercised in dependency-light environments.
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
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        show_ail: bool = typer_mod.Option(False, "--show-ail"),
        show_policy: bool = typer_mod.Option(False, "--show-policy"),
        json_output: bool = typer_mod.Option(False, "--json"),
    ) -> None:
        raise typer_mod.Exit(
            trace_command(
                run_id,
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
    ) -> None:
        raise typer_mod.Exit(
            memory_command(action, arg, from_run=from_run, data_dir=data_dir, verbose=verbose)
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
            )
        )

    @app.command("ail")
    def _typer_ail(
        action: str = typer_mod.Argument("validate"),
        file: str | None = typer_mod.Argument(None),
        verbose: bool = typer_mod.Option(False, "--verbose"),
    ) -> None:
        raise typer_mod.Exit(ail_command(action, file, verbose=verbose))


def main(argv: list[str] | None = None) -> int:
    if _HAS_TUI and argv is None:
        if len(sys.argv) == 1 and sys.stdin.isatty():
            return repl_command()
        app()
        return 0
    return fallback_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())


