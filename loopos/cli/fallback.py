"""Standard-library CLI fallback used when Typer is unavailable."""

from __future__ import annotations

import argparse
import sys

from loopos.cli.commands import (
    ail_command,
    config_command,
    db_command,
    gateway_command,
    goal_command,
    history_command,
    memory_command,
    models_command,
    policy_command,
    profile_command,
    providers_command,
    replay_command,
    resume_command,
    review_command,
    run_command,
    skills_command,
    status_command,
    tasks_command,
    tools_command,
    trace_command,
    triggers_command,
    worktrees_command,
)


def fallback_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="loopos", description="LoopOS terminal-native AI-ISA runtime.")
    sub = parser.add_subparsers(dest="command")

    run_parser = sub.add_parser("run")
    run_parser.add_argument("goal")
    run_parser.add_argument("--max-steps", type=int, default=20)
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument("--yes", action="store_true")
    run_parser.add_argument("--verbose", action="store_true")
    run_parser.add_argument("--data-dir", default=".loopos")
    run_parser.add_argument("--workspace", default=".")
    run_parser.add_argument("--mode", choices=["guarded", "dry_run"], default="guarded")
    run_parser.add_argument("--show-ail", action="store_true")
    run_parser.add_argument("--show-policy", action="store_true")
    run_parser.add_argument("--json", dest="json_output", action="store_true")
    run_parser.add_argument("--goal-option")
    run_parser.add_argument("--confirm-goal", action="store_true")
    run_parser.add_argument("--memory", choices=["on", "off"], default="on")
    run_parser.add_argument("--propose-memory", action="store_true")
    run_parser.add_argument("--llm-provider", choices=["mock", "openai-compatible"], default="mock")

    resume_parser = sub.add_parser("resume")
    resume_parser.add_argument("run_id")
    resume_parser.add_argument("--data-dir", default=".loopos")
    resume_parser.add_argument("--approve", action="store_true")
    resume_parser.add_argument("--deny", action="store_true")
    resume_parser.add_argument("--verbose", action="store_true")
    resume_parser.add_argument("--json", dest="json_output", action="store_true")

    status_parser = sub.add_parser("status")
    status_parser.add_argument("run_id")
    status_parser.add_argument("--verbose", action="store_true")
    status_parser.add_argument("--data-dir", default=".loopos")

    history_parser = sub.add_parser("history")
    history_parser.add_argument("run_id")
    history_parser.add_argument("--data-dir", default=".loopos")

    skills_parser = sub.add_parser("skills")
    skills_parser.add_argument("action", nargs="?", default="list")
    skills_parser.add_argument("arg", nargs="?")
    skills_parser.add_argument("--data-dir", default=".loopos")

    trace_parser = sub.add_parser("trace")
    trace_parser.add_argument("run_id")
    trace_parser.add_argument("--data-dir", default=".loopos")
    trace_parser.add_argument("--show-ail", action="store_true")
    trace_parser.add_argument("--show-policy", action="store_true")
    trace_parser.add_argument("--json", dest="json_output", action="store_true")

    step_parser = sub.add_parser("step")
    step_parser.add_argument("action")
    step_parser.add_argument("run_id")
    step_parser.add_argument("step", type=int)
    step_parser.add_argument("--data-dir", default=".loopos")
    step_parser.add_argument("--json", dest="json_output", action="store_true")

    tools_parser = sub.add_parser("tools")
    tools_parser.add_argument("action", nargs="?", default="list")
    tools_parser.add_argument("--workspace", default=".")
    tools_parser.add_argument("--json", dest="json_output", action="store_true")

    goal_parser = sub.add_parser("goal")
    goal_parser.add_argument("action")
    goal_parser.add_argument("raw_goal")
    goal_parser.add_argument("--option")
    goal_parser.add_argument("--confirm", action="store_true")
    goal_parser.add_argument("--json", dest="json_output", action="store_true")

    db_parser = sub.add_parser("db")
    db_parser.add_argument("action", nargs="?", default="detect")
    db_parser.add_argument("arg", nargs="?")
    db_parser.add_argument("--cmd")
    db_parser.add_argument("--target")
    db_parser.add_argument("--source")
    db_parser.add_argument("--backup-id")
    db_parser.add_argument("--migration")
    db_parser.add_argument("--data-dir", default=".loopos")
    db_parser.add_argument("--workspace", default=".")
    db_parser.add_argument("--yes", action="store_true")
    db_parser.add_argument("--json", dest="json_output", action="store_true")

    tasks_parser = sub.add_parser("tasks")
    tasks_parser.add_argument("action", nargs="?", default="list")
    tasks_parser.add_argument("arg", nargs="?")
    tasks_parser.add_argument("--data-dir", default=".loopos")
    tasks_parser.add_argument("--quick-win", action="store_true")
    tasks_parser.add_argument("--json", dest="json_output", action="store_true")
    tasks_parser.add_argument("--goal")
    tasks_parser.add_argument("--type", dest="task_type", default="coordination")
    tasks_parser.add_argument("--text")
    tasks_parser.add_argument("--content")
    tasks_parser.add_argument("--title")
    tasks_parser.add_argument("--requires-worktree", action="store_true")
    tasks_parser.add_argument("--ready", action="store_true")

    triggers_parser = sub.add_parser("triggers")
    triggers_parser.add_argument("action", nargs="?", default="list")
    triggers_parser.add_argument("trigger_id", nargs="?")
    triggers_parser.add_argument("--data-dir", default=".loopos")

    worktrees_parser = sub.add_parser("worktrees")
    worktrees_parser.add_argument("action", nargs="?", default="list")
    worktrees_parser.add_argument("task_id", nargs="?")
    worktrees_parser.add_argument("--data-dir", default=".loopos")
    worktrees_parser.add_argument("--workspace", default=".")
    worktrees_parser.add_argument("--dry-run", action="store_true", default=True)
    worktrees_parser.add_argument("--execute", dest="dry_run", action="store_false")
    worktrees_parser.add_argument("--yes", action="store_true")

    review_parser = sub.add_parser("review")
    review_parser.add_argument("action", nargs="?", default="list")
    review_parser.add_argument("task_id", nargs="?")
    review_parser.add_argument("--data-dir", default=".loopos")
    review_parser.add_argument("--producer", default="producer")
    review_parser.add_argument("--verifier", default="verifier")
    review_parser.add_argument("--reviewer", default="reviewer")
    review_parser.add_argument("--actor")
    review_parser.add_argument("--note")

    providers_parser = sub.add_parser("providers")
    providers_parser.add_argument("action", nargs="?", default="list")
    providers_parser.add_argument("value", nargs="?")
    providers_parser.add_argument("--json", dest="json_output", action="store_true")

    models_parser = sub.add_parser("models")
    models_parser.add_argument("action", nargs="?", default="route")
    models_parser.add_argument("--task", default="general")
    models_parser.add_argument("--input", dest="input_kind")
    models_parser.add_argument("--secret", action="store_true")

    gateway_parser = sub.add_parser("gateway")
    gateway_parser.add_argument("action", nargs="?", default="simulate")
    gateway_parser.add_argument("channel", nargs="?", default="telegram")
    gateway_parser.add_argument("text", nargs="?", default="hello")
    gateway_parser.add_argument("--user-id", default="user")
    gateway_parser.add_argument("--data-dir", default=".loopos")
    gateway_parser.add_argument("--run-id")
    gateway_parser.add_argument("--risk", default="medium")
    gateway_parser.add_argument("--reason-code")
    gateway_parser.add_argument("--approve", action="store_true")
    gateway_parser.add_argument("--deny", action="store_true")

    memory_parser = sub.add_parser("memory")
    memory_parser.add_argument("action", nargs="?", default="list")
    memory_parser.add_argument("arg", nargs="?")
    memory_parser.add_argument("--from-run")
    memory_parser.add_argument("--verbose", action="store_true")
    memory_parser.add_argument("--data-dir", default=".loopos")

    profile_parser = sub.add_parser("profile")
    profile_parser.add_argument("action", nargs="?", default="show")
    profile_parser.add_argument("key", nargs="?")
    profile_parser.add_argument("value", nargs="?")
    profile_parser.add_argument("--data-dir", default=".loopos")

    policy_parser = sub.add_parser("policy")
    policy_parser.add_argument("action", nargs="?", default="list")
    policy_parser.add_argument("policy_id", nargs="?")
    policy_parser.add_argument("--scope")
    policy_parser.add_argument("--input", dest="input_json")
    policy_parser.add_argument("--verbose", action="store_true")
    policy_parser.add_argument("--cmd")
    policy_parser.add_argument("--data-dir", default=".loopos")

    ail_parser = sub.add_parser("ail")
    ail_parser.add_argument("action", nargs="?", default="validate")
    ail_parser.add_argument("file", nargs="?")
    ail_parser.add_argument("--verbose", action="store_true")

    config_parser = sub.add_parser("config")
    config_parser.add_argument("--data-dir", default=".loopos")

    args = parser.parse_args(argv)
    if args.command == "run":
        return run_command(
            args.goal,
            max_steps=args.max_steps,
            dry_run=args.dry_run,
            yes=args.yes,
            verbose=args.verbose,
            data_dir=args.data_dir,
            memory=args.memory,
            propose_memory=args.propose_memory,
            llm_provider=args.llm_provider,
            workspace=args.workspace,
            mode=args.mode,
            show_ail=args.show_ail,
            show_policy=args.show_policy,
            json_output=args.json_output,
            goal_option=args.goal_option,
            confirm_goal=args.confirm_goal,
        )
    if args.command == "resume":
        return resume_command(
            args.run_id,
            data_dir=args.data_dir,
            approve=args.approve,
            deny=args.deny,
            verbose=args.verbose,
            json_output=args.json_output,
        )
    if args.command == "status":
        return status_command(args.run_id, data_dir=args.data_dir, verbose=args.verbose)
    if args.command == "history":
        return history_command(args.run_id, data_dir=args.data_dir)
    if args.command == "skills":
        return skills_command(args.action, args.arg, data_dir=args.data_dir)
    if args.command == "trace":
        return trace_command(
            args.run_id,
            data_dir=args.data_dir,
            show_ail=args.show_ail,
            show_policy=args.show_policy,
            json_output=args.json_output,
        )
    if args.command == "step":
        if args.action != "replay":
            print(f"Unknown step action: {args.action}", file=sys.stderr)
            return 1
        return replay_command(
            args.run_id,
            args.step,
            data_dir=args.data_dir,
            json_output=args.json_output,
        )
    if args.command == "tools":
        return tools_command(
            args.action,
            workspace=args.workspace,
            json_output=args.json_output,
        )
    if args.command == "goal":
        return goal_command(
            args.action,
            args.raw_goal,
            option=args.option,
            confirmed=args.confirm,
            json_output=args.json_output,
        )
    if args.command == "db":
        return db_command(
            args.action,
            args.arg,
            cmd=args.cmd,
            target=args.target,
            source=args.source,
            backup_id=args.backup_id,
            migration=args.migration,
            data_dir=args.data_dir,
            workspace=args.workspace,
            yes=args.yes,
            json_output=args.json_output,
        )
    if args.command == "tasks":
        return tasks_command(
            args.action,
            args.arg,
            data_dir=args.data_dir,
            quick_win=args.quick_win,
            json_output=args.json_output,
            goal=args.goal,
            task_type=args.task_type,
            text=args.text,
            content=args.content,
            title=args.title,
            requires_worktree=args.requires_worktree,
            ready=args.ready,
        )
    if args.command == "triggers":
        return triggers_command(args.action, args.trigger_id, data_dir=args.data_dir)
    if args.command == "worktrees":
        return worktrees_command(
            args.action,
            args.task_id,
            data_dir=args.data_dir,
            workspace=args.workspace,
            dry_run=args.dry_run,
            yes=args.yes,
        )
    if args.command == "review":
        return review_command(
            args.action,
            args.task_id,
            data_dir=args.data_dir,
            producer=args.producer,
            verifier=args.verifier,
            reviewer=args.reviewer,
            actor=args.actor,
            note=args.note,
        )
    if args.command == "providers":
        return providers_command(args.action, args.value, json_output=args.json_output)
    if args.command == "models":
        return models_command(
            args.action,
            task=args.task,
            input_kind=args.input_kind,
            secret=args.secret,
        )
    if args.command == "gateway":
        return gateway_command(
            args.action,
            args.channel,
            args.text,
            user_id=args.user_id,
            data_dir=args.data_dir,
            run_id=args.run_id,
            risk=args.risk,
            reason_code=args.reason_code,
            approve=args.approve,
            deny=args.deny,
        )
    if args.command == "memory":
        return memory_command(
            args.action,
            args.arg,
            from_run=args.from_run,
            data_dir=args.data_dir,
            verbose=args.verbose,
        )
    if args.command == "profile":
        return profile_command(args.action, args.key, args.value, data_dir=args.data_dir)
    if args.command == "policy":
        return policy_command(
            args.action,
            args.policy_id,
            scope=args.scope,
            input_json=args.input_json,
            data_dir=args.data_dir,
            verbose=args.verbose,
            cmd=args.cmd,
        )
    if args.command == "ail":
        return ail_command(args.action, args.file, verbose=args.verbose)
    if args.command == "config":
        return config_command(data_dir=args.data_dir)
    parser.print_help()
    return 0
