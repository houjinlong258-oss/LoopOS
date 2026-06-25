"""Standard-library CLI fallback used when Typer is unavailable."""

from __future__ import annotations

import argparse
import json
import sys

from loopos.cli.commands import (
    ail_command,
    config_command,
    computer_command,
    db_command,
    files_command,
    gateway_command,
    goal_command,
    history_command,
    imagine_command,
    lail_encode_command,
    loop_artifacts_command,
    loop_deliver_command,
    loop_diff_command,
    loop_optimize_command,
    loop_repair_command,
    loop_replay_command,
    loop_review_command,
    loop_run_command,
    loop_status_command,
    memory_command,
    memory_compile_command,
    locale_command,
    mode_command,
    models_command,
    hookify_list_command,
    hookify_enable_command,
    hookify_disable_command,
    hookify_test_command,
    nodes_command,
    policy_command,
    profile_command,
    providers_command,
    registry_command,
    release_command,
    replay_command,
    resume_command,
    review_command,
    run_command,
    search_command,
    index_command,
    skills_command,
    status_command,
    tasks_command,
    token_command,
    tools_command,
    trace_command,
    triggers_command,
    worktrees_command,
    # v0.3
    workbench_command,
    adapters_command,
    providers_runtime_command,
    model_call_command,
    opengod_command,
    session_command,
    readiness_command,
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
    trace_parser.add_argument("value", nargs="?")
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
    tools_parser.add_argument("query", nargs="?")
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
    db_parser.add_argument("--human", dest="human_output", action="store_true")

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

    index_parser = sub.add_parser("index")
    index_parser.add_argument("action", nargs="?", default="status")
    index_parser.add_argument("--workspace", default=".")
    index_parser.add_argument("--data-dir", default=".loopos")

    search_parser = sub.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument("value", nargs="?")
    search_parser.add_argument("--workspace", default=".")
    search_parser.add_argument("--data-dir", default=".loopos")
    search_parser.add_argument("--limit", type=int, default=20)

    files_parser = sub.add_parser("files")
    files_parser.add_argument("action")
    files_parser.add_argument("query")
    files_parser.add_argument("--workspace", default=".")
    files_parser.add_argument("--data-dir", default=".loopos")

    mode_parser = sub.add_parser("mode")
    mode_parser.add_argument("action", nargs="?", default="status")
    mode_parser.add_argument("value", nargs="?")
    mode_parser.add_argument("--data-dir", default=".loopos")
    mode_parser.add_argument("--private-data", action="store_true")
    mode_parser.add_argument("--sanitized", action="store_true")
    mode_parser.add_argument("--cloud-consent", action="store_true")

    registry_parser = sub.add_parser("registry")
    registry_parser.add_argument("action", nargs="?", default="list")
    registry_parser.add_argument("value", nargs="?")
    registry_parser.add_argument("--type", dest="plugin_type")
    registry_parser.add_argument("--data-dir", default=".loopos")

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
    review_parser.add_argument("--run-id")
    review_parser.add_argument("--high-risk", action="store_true")
    review_parser.add_argument("--maintainability-blocked", action="store_true")
    review_parser.add_argument("--diff", dest="diff_file")
    review_parser.add_argument("--human", dest="human_output", action="store_true")

    providers_parser = sub.add_parser("providers")
    providers_parser.add_argument("action", nargs="?", default="list")
    providers_parser.add_argument("value", nargs="?")
    providers_parser.add_argument("--provider", dest="provider_id")
    providers_parser.add_argument("--json", dest="json_output", action="store_true")

    provider_parser = sub.add_parser("provider")
    provider_parser.add_argument("action", nargs="?", default="list")
    provider_parser.add_argument("value", nargs="?")
    provider_parser.add_argument("--provider", dest="provider_id")
    provider_parser.add_argument("--json", dest="json_output", action="store_true")

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

    computer_parser = sub.add_parser("computer")
    computer_parser.add_argument("action", nargs="?", default="run")
    computer_parser.add_argument("task", nargs="?")
    computer_parser.add_argument("--backend", default="fake")
    computer_parser.add_argument("--allow-computer-control", action="store_true")
    computer_parser.add_argument("--approve-each-action", action="store_true")
    computer_parser.add_argument("--sandbox", action="store_true")
    computer_parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=True)
    computer_parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    computer_parser.add_argument("--latest", action="store_true")
    computer_parser.add_argument("--data-dir", default=".loopos")
    computer_parser.add_argument("--json", dest="json_output", action="store_true")

    token_parser = sub.add_parser("token")
    token_parser.add_argument("action", nargs="?", default="report")
    token_parser.add_argument("--latest", action="store_true")
    token_parser.add_argument("--data-dir", default=".loopos")
    token_parser.add_argument("--json", dest="json_output", action="store_true")

    nodes_parser = sub.add_parser("nodes")
    nodes_parser.add_argument("action", nargs="?", default="list")
    nodes_parser.add_argument("--code")
    nodes_parser.add_argument("--json", dest="json_output", action="store_true")

    memory_parser = sub.add_parser("memory")
    memory_parser.add_argument("action", nargs="?", default="list")
    memory_parser.add_argument("arg", nargs="?")
    memory_parser.add_argument("--from-run")
    memory_parser.add_argument("--verbose", action="store_true")
    memory_parser.add_argument("--data-dir", default=".loopos")
    memory_parser.add_argument("--role")
    # v0.4.0 closeout: --items and --items-file gate the new
    # ``memory compile`` action without breaking v0.1 ``memory
    # list`` / ``memory show`` / etc.
    memory_parser.add_argument("--items", default=None)
    memory_parser.add_argument("--items-file", dest="items_file", default=None)
    memory_parser.add_argument("--goal", dest="goal_summary", default="")
    memory_parser.add_argument("--gap", dest="current_gap", default="")
    memory_parser.add_argument("--token-budget", dest="token_budget",
                               type=int, default=900)
    memory_parser.add_argument("--run-id", dest="run_id", default=None)
    memory_parser.add_argument("--iteration", dest="iteration_index",
                               type=int, default=0)
    memory_parser.add_argument("--json", dest="json_output", action="store_true")

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
    policy_parser.add_argument("--human", dest="human_output", action="store_true")

    ail_parser = sub.add_parser("ail")
    ail_parser.add_argument("action", nargs="?", default="validate")
    ail_parser.add_argument("file", nargs="?")
    ail_parser.add_argument("--verbose", action="store_true")

    lail_parser = sub.add_parser("lail")
    lail_parser.add_argument("action", nargs="?", default="encode")
    lail_parser.add_argument("value", nargs="?")
    lail_parser.add_argument("--json", dest="json_output", action="store_true")
    lail_parser.add_argument("--kind", default="iteration_started")
    lail_parser.add_argument("--run-id", dest="run_id", default="run_local")
    lail_parser.add_argument("--iteration", dest="iteration_index",
                             type=int, default=0)
    lail_parser.add_argument("--trace-id", dest="trace_id", default=None)
    lail_parser.add_argument("--payload", default=None)

    config_parser = sub.add_parser("config")
    config_parser.add_argument("--data-dir", default=".loopos")

    # --- v0.3 ----------------------------------------------------------------
    workbench_parser = sub.add_parser("workbench")
    workbench_parser.add_argument("goal_path", nargs="?")
    workbench_parser.add_argument("--adapter", default="mock")
    workbench_parser.add_argument("--model", default="mock-model")
    workbench_parser.add_argument("--provider", default="mock")
    workbench_parser.add_argument("--mode", default="single")
    workbench_parser.add_argument("--budget-usd", type=float, default=0.0)
    workbench_parser.add_argument("--mad-dog", action="store_true")
    workbench_parser.add_argument("--allow-live-provider", action="store_true")
    workbench_parser.add_argument("--no-dry-run", action="store_true")
    workbench_parser.add_argument("--watch", action="store_true")
    workbench_parser.add_argument("--json", dest="json_output", action="store_true")
    workbench_parser.add_argument("--project", default="")

    adapters_parser = sub.add_parser("adapters")
    adapters_parser.add_argument("action", nargs="?", default="list")
    adapters_parser.add_argument("value", nargs="?")
    adapters_parser.add_argument("--json", dest="json_output", action="store_true")

    providers_runtime_parser = sub.add_parser("providers-runtime")
    providers_runtime_parser.add_argument("action", nargs="?", default="list")
    providers_runtime_parser.add_argument("value", nargs="?")
    providers_runtime_parser.add_argument("--model", default="mock-model")
    providers_runtime_parser.add_argument("--no-dry-run", action="store_true")
    providers_runtime_parser.add_argument("--json", dest="json_output", action="store_true")

    model_call_parser = sub.add_parser("model-call")
    model_call_parser.add_argument("prompt_path")
    model_call_parser.add_argument("--provider", default="mock")
    model_call_parser.add_argument("--model", default="mock-model")
    model_call_parser.add_argument("--no-dry-run", action="store_true")
    model_call_parser.add_argument("--allow-live-provider", action="store_true")
    model_call_parser.add_argument("--budget-usd", type=float, default=0.0)
    model_call_parser.add_argument("--confirm", action="store_true")
    model_call_parser.add_argument("--json", dest="json_output", action="store_true")

    opengod_parser = sub.add_parser("opengod")
    opengod_parser.add_argument("goal_id", nargs="?", default="goal_demo")
    opengod_parser.add_argument("--goal-title", default="")
    opengod_parser.add_argument("--goal-risk", default="medium")
    opengod_parser.add_argument("--fusion-mode", default="single")
    opengod_parser.add_argument("--fusion-score", type=int, default=0)
    opengod_parser.add_argument("--hard-fail-count", type=int, default=0)
    opengod_parser.add_argument("--readiness-status", default="unknown")
    opengod_parser.add_argument("--adapter-id", default="")
    opengod_parser.add_argument("--live-provider-calls", action="store_true")
    opengod_parser.add_argument("--budget-used-usd", type=float, default=0.0)
    opengod_parser.add_argument("--budget-max-usd", type=float, default=0.0)
    opengod_parser.add_argument("--max-budget-usd", type=float, default=1.0)
    opengod_parser.add_argument("--reserve-usd", type=float, default=0.10)
    opengod_parser.add_argument("--json", dest="json_output", action="store_true")

    session_parser = sub.add_parser("session")
    session_parser.add_argument("action", nargs="?", default="list")
    session_parser.add_argument("session_id", nargs="?")
    session_parser.add_argument("--data-dir", default=".loopos")
    session_parser.add_argument("--json", dest="json_output", action="store_true")

    readiness_parser = sub.add_parser("readiness")
    readiness_parser.add_argument("action", nargs="?", default="check")
    readiness_parser.add_argument("--json", dest="json_output", action="store_true")

    locale_parser = sub.add_parser("locale")
    locale_parser.add_argument("action", nargs="?", default="show")
    locale_parser.add_argument("locale_id", nargs="?")
    locale_parser.add_argument("--json", dest="json_output", action="store_true")

    # v0.4.x: hookify
    hookify_parser = sub.add_parser("hookify")
    hookify_parser.add_argument("action", nargs="?", default="list")
    hookify_parser.add_argument("name", nargs="?")
    hookify_parser.add_argument("--event", dest="event", default="all")
    hookify_parser.add_argument("--data", dest="data", default=None)
    hookify_parser.add_argument(
        "--json", dest="json_output", action="store_true", default=True,
    )
    hookify_parser.add_argument(
        "--human", dest="json_output", action="store_false",
    )
    hookify_parser.add_argument("--data-dir", dest="data_dir", default=".loopos")

    # v0.4.0: Loop Engineering commands
    loop_parser = sub.add_parser("loop")
    loop_parser.add_argument("action", nargs="?", default="run")
    loop_parser.add_argument("goal", nargs="?")
    loop_parser.add_argument("--max-iterations", type=int, default=3)
    loop_parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    loop_parser.add_argument("--real-executor", dest="real_executor", action="store_true")
    loop_parser.add_argument("--sandbox", dest="sandbox", action="store_true", default=True)
    loop_parser.add_argument("--no-sandbox", dest="sandbox", action="store_false")
    loop_parser.add_argument("--repo-path", dest="repo_path", default=None)
    loop_parser.add_argument("--test-command", dest="test_command", default=None)
    loop_parser.add_argument(
        "--completion-promise",
        dest="completion_promise",
        default=None,
        help="Literal substring: when an iteration's emitted surface "
        "contains this string, the loop declares early success and stops. "
        "Always bounded by --max-iterations.",
    )
    loop_parser.add_argument("--mad-dog", dest="mad_dog", action="store_true")
    loop_parser.add_argument("--json", dest="json_output", action="store_true")
    loop_parser.add_argument("--run-id", dest="run_id", default=None)
    loop_parser.add_argument("--latest", dest="latest", action="store_true")
    loop_parser.add_argument("--data-dir", dest="data_dir", default=None)

    imagine_parser = sub.add_parser("imagine")
    imagine_parser.add_argument("prompt")
    imagine_parser.add_argument("--mode", default="brainstorm",
                                choices=["brainstorm", "wild", "alternatives",
                                         "architecture", "repair", "optimization"])
    imagine_parser.add_argument("--max-candidates", type=int, default=3)
    imagine_parser.add_argument("--json", dest="json_output", action="store_true")


    release_parser = sub.add_parser("release")
    release_parser.add_argument("action", nargs="?", default="check")
    release_parser.add_argument("--version", default="0.1.0")
    release_parser.add_argument("--source", "--workspace", default=".")
    release_parser.add_argument("--output", default="dist")
    release_parser.add_argument("--no-zip", action="store_true")
    release_parser.add_argument("--strict", action="store_true")
    release_parser.add_argument("--ignore-local-only", action="store_true")
    release_parser.add_argument("--strict-source", action="store_true")
    release_parser.add_argument("--deep", action="store_true")
    release_parser.add_argument("--timeout-per-check", type=int, default=60)
    release_parser.add_argument("--global-timeout", type=int, default=300)
    release_parser.add_argument("--target", default="founding-preview")
    release_parser.add_argument("--json", dest="json_output", action="store_true")

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
            args.value,
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
            args.query,
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
            human_output=args.human_output,
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
    if args.command == "index":
        return index_command(args.action, workspace=args.workspace, data_dir=args.data_dir)
    if args.command == "search":
        return search_command(
            args.query,
            args.value,
            workspace=args.workspace,
            data_dir=args.data_dir,
            limit=args.limit,
        )
    if args.command == "files":
        return files_command(
            args.action,
            args.query,
            workspace=args.workspace,
            data_dir=args.data_dir,
        )
    if args.command == "mode":
        return mode_command(
            args.action,
            args.value,
            data_dir=args.data_dir,
            private_data=args.private_data,
            sanitized=args.sanitized,
            cloud_consent=args.cloud_consent,
        )
    if args.command == "registry":
        return registry_command(
            args.action,
            args.value,
            plugin_type=args.plugin_type,
            data_dir=args.data_dir,
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
            run_id=args.run_id,
            high_risk=args.high_risk,
            maintainability_blocked=args.maintainability_blocked,
            diff_file=args.diff_file,
            human_output=args.human_output,
        )
    if args.command == "providers":
        return providers_command(args.action, args.value or args.provider_id, json_output=args.json_output)
    if args.command == "provider":
        return providers_command(args.action, args.value or args.provider_id, json_output=args.json_output)
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
    if args.command == "locale":
        return locale_command(
            args.action,
            args.locale_id,
            json_output=args.json_output,
        )
    if args.command == "hookify":
        if args.action == "list":
            return hookify_list_command(
                data_dir=args.data_dir, json_output=args.json_output,
            )
        if not args.name:
            print(
                json.dumps(
                    {"status": "error", "error_code": "name_required",
                     "message": f"hookify {args.action!r} requires a rule name"},
                )
            )
            return 1
        if args.action == "enable":
            return hookify_enable_command(args.name, data_dir=args.data_dir)
        if args.action == "disable":
            return hookify_disable_command(args.name, data_dir=args.data_dir)
        if args.action == "test":
            return hookify_test_command(
                args.name, event=args.event, data=args.data, data_dir=args.data_dir,
            )
        print(
            json.dumps(
                {"status": "error", "error_code": "unknown_action",
                 "message": f"unknown hookify action: {args.action!r}"},
            )
        )
        return 1
    if args.command == "computer":
        return computer_command(
            args.action,
            args.task,
            backend=args.backend,
            allow_computer_control=args.allow_computer_control,
            approve_each_action=args.approve_each_action,
            sandbox=args.sandbox,
            dry_run=args.dry_run,
            latest=args.latest,
            data_dir=args.data_dir,
            json_output=args.json_output,
        )
    if args.command == "token":
        return token_command(
            args.action,
            latest=args.latest,
            data_dir=args.data_dir,
            json_output=args.json_output,
        )
    if args.command == "nodes":
        return nodes_command(args.action, code=args.code, json_output=args.json_output)
    if args.command == "memory":
        # v0.4.0 closeout: `memory compile` is the new command.
        # v0.1 `memory <action> <arg>` is preserved for back-compat.
        if args.action == "compile":
            # ``--role`` is the v0.1 surface; ``--target-role`` is the
            # v0.4 closeout surface. We prefer the closeout one when
            # the user provided it; otherwise we fall back to the
            # legacy ``--role`` (which v0.4 also accepts via the
            # ``target_role`` alias below).
            target_role = getattr(args, "target_role", None) or args.role
            return memory_compile_command(
                items=args.items or "[]",
                items_file=args.items_file,
                target_role=target_role,
                goal_summary=args.goal_summary,
                current_gap=args.current_gap,
                token_budget=args.token_budget,
                run_id=args.run_id,
                iteration_index=args.iteration_index,
                json_output=args.json_output,
            )
        return memory_command(
            args.action,
            args.arg,
            from_run=args.from_run,
            data_dir=args.data_dir,
            verbose=args.verbose,
            role=args.role,
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
            human_output=args.human_output,
        )
    if args.command == "ail":
        return ail_command(args.action, args.file, verbose=args.verbose)
    if args.command == "lail":
        if args.action == "encode":
            payload = getattr(args, "payload", None)
            return lail_encode_command(
                kind=args.kind,
                run_id=args.run_id,
                iteration_index=args.iteration_index,
                trace_id=args.trace_id,
                payload=payload,
                json_output=args.json_output,
            )
        return 2
    if args.command == "config":
        return config_command(data_dir=args.data_dir)
    if args.command == "release":
        return release_command(
            args.action,
            version=args.version,
            source=args.source,
            output=args.output,
            no_zip=args.no_zip,
            strict=args.strict,
            ignore_local_only=args.ignore_local_only,
            strict_source=args.strict_source,
            deep=args.deep,
            timeout_per_check=args.timeout_per_check,
            global_timeout=args.global_timeout,
            target=args.target,
            json_output=args.json_output,
        )
    if args.command == "workbench":
        return workbench_command(
            args.goal_path,
            adapter=args.adapter,
            model=args.model,
            provider=args.provider,
            mode=args.mode,
            budget_usd=args.budget_usd,
            mad_dog=args.mad_dog,
            allow_live_provider=args.allow_live_provider,
            dry_run=not args.no_dry_run,
            watch=args.watch,
            json_output=args.json_output,
            project=args.project,
        )
    if args.command == "adapters":
        return adapters_command(args.action, args.value, json_output=args.json_output)
    if args.command == "providers-runtime":
        return providers_runtime_command(
            args.action,
            args.value,
            model=args.model,
            dry_run=not args.no_dry_run,
            json_output=args.json_output,
        )
    if args.command == "model-call":
        return model_call_command(
            args.prompt_path,
            provider=args.provider,
            model=args.model,
            dry_run=not args.no_dry_run,
            allow_live_provider=args.allow_live_provider,
            budget_usd=args.budget_usd,
            confirm=args.confirm,
            json_output=args.json_output,
        )
    if args.command == "opengod":
        return opengod_command(
            args.goal_id,
            goal_title=args.goal_title,
            goal_risk=args.goal_risk,
            fusion_mode=args.fusion_mode,
            fusion_score=args.fusion_score,
            hard_fail_count=args.hard_fail_count,
            readiness_status=args.readiness_status,
            adapter_id=args.adapter_id,
            live_provider_calls=args.live_provider_calls,
            budget_used_usd=args.budget_used_usd,
            budget_max_usd=args.budget_max_usd,
            max_budget_usd=args.max_budget_usd,
            reserve_usd=args.reserve_usd,
            json_output=args.json_output,
        )
    if args.command == "session":
        return session_command(
            args.action,
            args.session_id,
            data_dir=args.data_dir,
            json_output=args.json_output,
        )
    if args.command == "readiness":
        return readiness_command(args.action, json_output=args.json_output)
    if args.command == "loop":
        rid = args.run_id
        if args.latest:
            rid = "latest"
        if args.action == "run":
            return loop_run_command(
                goal=args.goal,
                max_iterations=args.max_iterations,
                dry_run=args.dry_run,
                real_executor=args.real_executor,
                sandbox=args.sandbox,
                repo_path=args.repo_path,
                test_command=args.test_command,
                json_output=args.json_output,
                run_id=rid,
                data_dir=args.data_dir,
                completion_promise=getattr(args, "completion_promise", None),
            )
        if args.action == "status":
            return loop_status_command(
                run_id=rid, json_output=args.json_output,
                data_dir=args.data_dir,
            )
        if args.action == "review":
            return loop_review_command(
                mad_dog=args.mad_dog, json_output=args.json_output,
                run_id=rid, data_dir=args.data_dir,
            )
        if args.action == "repair":
            return loop_repair_command(
                json_output=args.json_output,
                run_id=rid, data_dir=args.data_dir,
            )
        if args.action == "optimize":
            return loop_optimize_command(
                json_output=args.json_output,
                run_id=rid, data_dir=args.data_dir,
            )
        if args.action == "deliver":
            return loop_deliver_command(
                run_id=rid, json_output=args.json_output,
                data_dir=args.data_dir,
            )
        if args.action == "replay":
            return loop_replay_command(
                run_id=rid, json_output=args.json_output,
                data_dir=args.data_dir,
            )
        if args.action == "diff":
            return loop_diff_command(
                run_id=rid, json_output=args.json_output,
                data_dir=args.data_dir,
            )
        if args.action == "artifacts":
            return loop_artifacts_command(
                run_id=rid, json_output=args.json_output,
                data_dir=args.data_dir,
            )
        return 2
    if args.command == "imagine":
        return imagine_command(
            prompt=args.prompt,
            mode=args.mode,
            max_candidates=args.max_candidates,
            json_output=args.json_output,
        )
    parser.print_help()
    return 0

