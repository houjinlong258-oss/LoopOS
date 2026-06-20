"""LoopOS CLI/FLI entry point."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any

from loopos.cli.commands import (
    ail_command as ail_command,
    config_command as config_command,
    gateway_command as gateway_command,
    goal_command as goal_command,
    memory_command as memory_command,
    models_command as models_command,
    parse_goal_options as _parse_goal_options,
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

from loopos.core.state import LoopState
from loopos.goal import GoalNegotiator
from loopos.kernel import (
    KernelBoot,
    KernelConfig,
    KernelLoopEngine,
    ReplayEngine,
    RunManager,
    RunRecord,
    RunSpec,
    TraceStore,
)
from loopos.llm.providers import LLMProvider, MockLLMProvider, OpenAICompatibleProvider
from loopos.memory.extractor import MemoryProposalExtractor
from loopos.memory.repository import MemoryRepository
from loopos.syscalls import create_default_syscall_router

typer_mod: Any
ConsoleCls: Any
PanelCls: Any
TableCls: Any

try:  # Optional for local bootstrapping.
    import typer as typer_mod
    from rich.console import Console as ConsoleCls
    from rich.panel import Panel as PanelCls
    from rich.table import Table as TableCls

    _HAS_TUI = True
except Exception:  # pragma: no cover - exercised in dependency-light environments.
    typer_mod = None
    ConsoleCls = None
    PanelCls = None
    TableCls = None
    _HAS_TUI = False

if _HAS_TUI:
    app: Any = typer_mod.Typer(help="LoopOS terminal-native AI-ISA runtime.")
    console: Any = ConsoleCls()
else:
    app = None
    console = None


_paths = data_paths


def _render_state(state: LoopState, *, verbose: bool = False) -> str:
    payload: dict[str, Any] = {
        "run_id": state.run_id,
        "goal": state.goal,
        "status": state.status,
        "step_index": state.step_index,
        "progress_score": state.progress_score,
    }
    if state.last_observation:
        payload["last_observation"] = {
            "summary": state.last_observation.summary,
            "success": state.last_observation.success,
        }
        if verbose:
            payload["last_observation"]["stdout"] = state.last_observation.stdout
            payload["last_observation"]["stderr"] = state.last_observation.stderr
    if state.errors:
        payload["errors"] = state.errors
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _render_run(run: RunRecord, *, verbose: bool = False) -> str:
    payload: dict[str, Any] = {
        "run_id": run.run_id,
        "goal": run.goal,
        "status": run.status,
        "phase": run.phase,
        "step": run.step,
        "max_steps": run.max_steps,
        "workspace": run.workspace,
        "mode": run.mode,
        "progress_score": run.progress_score,
    }
    if run.pending_approval:
        payload["pending_approval"] = run.pending_approval.model_dump(mode="json")
    if run.errors:
        payload["errors"] = run.errors
    if verbose:
        payload["trace_event_ids"] = run.trace_event_ids
        payload["metadata"] = run.metadata
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _print_state(state: LoopState, *, verbose: bool = False) -> None:
    if _HAS_TUI:
        body = (
            f"Goal: {state.goal}\n"
            f"Status: {state.status}\n"
            f"Steps: {state.step_index}\n"
            f"Progress: {state.progress_score:.2f}"
        )
        console.print(PanelCls(body, title=f"LoopOS Run {state.run_id}"))
        if state.last_observation:
            obs = state.last_observation
            console.print(f"[bold]Last[/bold]: {obs.summary}")
            if verbose and (obs.stdout or obs.stderr):
                console.print(obs.stdout or obs.stderr)
    else:
        print(_render_state(state, verbose=verbose))


def _print_run(
    run: RunRecord,
    *,
    trace_store: TraceStore | None = None,
    verbose: bool = False,
    show_ail: bool = False,
    show_policy: bool = False,
    json_output: bool = False,
) -> None:
    events = trace_store.list(run.run_id) if trace_store else []
    if json_output:
        payload = json.loads(_render_run(run, verbose=verbose))
        if show_ail:
            payload["ail"] = [event.payload for event in events if event.kind == "instruction"]
        if show_policy:
            payload["policy"] = [event.payload for event in events if event.kind == "policy"]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if _HAS_TUI:
        body = (
            f"Goal: {run.goal}\nStatus: {run.status}\nPhase: {run.phase}\n"
            f"Steps: {run.step}/{run.max_steps}\nWorkspace: {run.workspace}\nMode: {run.mode}"
        )
        console.print(PanelCls(body, title=f"LoopOS Kernel Run {run.run_id}"))
        for event in events:
            if event.kind == "instruction":
                console.print(f"[{event.step}/{run.max_steps}] {event.payload.get('op', 'UNKNOWN')}")
        if run.pending_approval:
            console.print(
                f"[yellow]Approval required[/yellow]: {', '.join(run.pending_approval.reason_codes)}"
            )
        if show_ail:
            console.print_json(
                data=[event.payload for event in events if event.kind == "instruction"]
            )
        if show_policy:
            console.print_json(data=[event.payload for event in events if event.kind == "policy"])
    else:
        print(_render_run(run, verbose=verbose))


def run_command(
    goal: str,
    *,
    max_steps: int = 5,
    dry_run: bool = False,
    yes: bool = False,
    verbose: bool = False,
    data_dir: str | Path = ".loopos",
    memory: str = "on",
    propose_memory: bool = False,
    llm_provider: str = "mock",
    workspace: str | Path = ".",
    mode: str = "guarded",
    show_ail: bool = False,
    show_policy: bool = False,
    json_output: bool = False,
    goal_option: str | None = None,
) -> int:
    negotiator = GoalNegotiator()
    analysis = negotiator.analyze(goal)
    try:
        option_ids = _parse_goal_options(goal_option)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if analysis.ambiguous and not option_ids:
        proposal = negotiator.propose(goal)
        if json_output:
            print(proposal.model_dump_json(indent=2))
        else:
            print("LoopOS detected an ambiguous goal.\n")
            print("请选择一个执行方案：\n")
            for option in proposal.options:
                print(f"[{option.id}] {option.title}")
        return 4
    try:
        goal_spec = negotiator.finalize(goal, option_ids=option_ids)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    paths = _paths(data_dir)
    kernel_mode = "dry_run" if dry_run else mode
    if kernel_mode not in {"guarded", "dry_run"}:
        print(f"Unknown run mode: {kernel_mode}", file=sys.stderr)
        return 1
    runtime = KernelBoot().start(
        KernelConfig(
            workspace=str(workspace),
            data_dir=str(paths["base"]),
            auto_approve_medium=yes,
        )
    )
    repository = MemoryRepository(paths["base"]) if memory == "on" else None
    engine = KernelLoopEngine(runtime, memory_repository=repository)
    run = engine.run(
        RunSpec(
            goal=goal,
            workspace=str(Path(workspace).resolve()),
            mode=kernel_mode,  # type: ignore[arg-type]
            max_steps=max_steps,
            non_interactive=not sys.stdin.isatty(),
            metadata={"goal_spec": goal_spec.model_dump(mode="json")},
        )
    )
    if propose_memory and repository is not None:
        _propose_memory(repository, run.run_id, llm_provider)
    _print_run(
        run,
        trace_store=runtime.trace_store,
        verbose=verbose,
        show_ail=show_ail,
        show_policy=show_policy,
        json_output=json_output,
    )
    if run.status == "succeeded":
        return 0
    return 3 if run.status == "waiting_approval" else 1


def status_command(run_id: str, *, data_dir: str | Path = ".loopos", verbose: bool = False) -> int:
    try:
        run = RunManager(_paths(data_dir)["runs"]).load(run_id)
    except FileNotFoundError:
        print(f"Run not found: {run_id}", file=sys.stderr)
        return 1
    _print_run(run, verbose=verbose)
    return 0


def resume_command(
    run_id: str,
    *,
    data_dir: str | Path = ".loopos",
    approve: bool = False,
    deny: bool = False,
    verbose: bool = False,
    json_output: bool = False,
) -> int:
    try:
        paths = _paths(data_dir)
        existing = RunManager(paths["runs"]).load(run_id)
    except FileNotFoundError:
        print(f"Run not found: {run_id}", file=sys.stderr)
        return 1
    try:
        runtime = KernelBoot().start(
            KernelConfig(workspace=existing.workspace, data_dir=str(paths["base"]))
        )
        run = KernelLoopEngine(runtime, memory_repository=MemoryRepository(paths["base"])).resume(
            run_id, approve=approve, deny=deny
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    _print_run(run, trace_store=runtime.trace_store, verbose=verbose, json_output=json_output)
    if run.status == "succeeded":
        return 0
    return 3 if run.status == "waiting_approval" else 1


def history_command(run_id: str, *, data_dir: str | Path = ".loopos") -> int:
    events = TraceStore(_paths(data_dir)["events"]).list(run_id)
    if not events:
        print(f"No events for run: {run_id}")
        return 0
    if _HAS_TUI:
        table = TableCls(title=f"History {run_id}")
        table.add_column("step")
        table.add_column("type")
        table.add_column("payload")
        for event in events:
            table.add_row(str(event.step), event.type or event.kind or "run", json.dumps(event.payload, ensure_ascii=False)[:120])
        console.print(table)
    else:
        print(json.dumps([event.model_dump(mode="json") for event in events], ensure_ascii=False, indent=2))
    return 0


def trace_command(
    run_id: str,
    *,
    data_dir: str | Path = ".loopos",
    show_ail: bool = False,
    show_policy: bool = False,
    json_output: bool = False,
) -> int:
    events = TraceStore(_paths(data_dir)["events"]).list(run_id)
    if not events:
        print(f"No events for run: {run_id}", file=sys.stderr)
        return 1
    selected = events
    if show_ail and not show_policy:
        selected = [event for event in events if event.kind == "instruction"]
    elif show_policy and not show_ail:
        selected = [event for event in events if event.kind == "policy"]
    payload = [event.model_dump(mode="json") for event in selected]
    if json_output or not _HAS_TUI:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    table = TableCls(title=f"Trace {run_id}")
    table.add_column("step")
    table.add_column("kind")
    table.add_column("summary")
    for event in selected:
        summary = event.payload.get("op") or event.payload.get("summary") or event.type
        table.add_row(str(event.step), str(event.kind), str(summary)[:100])
    console.print(table)
    return 0


def replay_command(
    run_id: str,
    step: int,
    *,
    data_dir: str | Path = ".loopos",
    json_output: bool = False,
) -> int:
    paths = _paths(data_dir)
    try:
        durable = RunManager(paths["runs"]).load(run_id)
    except FileNotFoundError:
        durable = None
    result = ReplayEngine(TraceStore(paths["events"])).replay(run_id, step, durable=durable)
    if not result.events:
        print(f"No replayable events for run {run_id} step {step}", file=sys.stderr)
        return 1
    payload = result.model_dump(mode="json")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def tools_command(
    action: str = "list",
    *,
    workspace: str | Path = ".",
    json_output: bool = False,
) -> int:
    if action != "list":
        print(f"Unknown tools action: {action}", file=sys.stderr)
        return 1
    specs = create_default_syscall_router(workspace).registry.list()
    payload = [spec.model_dump(mode="json") for spec in specs]
    if json_output or not _HAS_TUI:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        table = TableCls(title="Kernel Syscalls")
        table.add_column("name")
        table.add_column("risk")
        table.add_column("policy scope")
        for spec in specs:
            table.add_row(spec.name, spec.risk, spec.policy_scope)
        console.print(table)
    return 0


def repl_command() -> int:
    """Minimal terminal shell over the public command functions."""

    print("LoopOS Kernel REPL. Commands: run, status, trace, tools, help, quit")
    while True:
        try:
            raw = input("loopos> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not raw:
            continue
        parts = shlex.split(raw)
        command = parts[0].lower()
        if command in {"quit", "exit"}:
            return 0
        if command == "help":
            print("run GOAL | status RUN_ID | trace RUN_ID | tools | quit")
        elif command == "run" and len(parts) > 1:
            run_command(" ".join(parts[1:]))
        elif command == "status" and len(parts) == 2:
            status_command(parts[1])
        elif command == "trace" and len(parts) == 2:
            trace_command(parts[1])
        elif command == "tools":
            tools_command()
        else:
            print(f"Unknown or incomplete command: {raw}")


def _llm_provider(name: str) -> LLMProvider:
    if name == "mock":
        return MockLLMProvider()
    if name == "openai-compatible":
        return OpenAICompatibleProvider()
    raise ValueError(f"unknown LLM provider: {name}")


def _propose_memory(repo: MemoryRepository, run_id: str, provider_name: str) -> None:
    extractor = MemoryProposalExtractor(_llm_provider(provider_name))
    events = repo.events.list(run_id)
    proposals, errors = extractor.extract(
        run_id=run_id,
        events=events,
        user_profile=repo.get_profile(),
    )
    for proposal in proposals:
        repo.propose(proposal)
    for error in errors:
        repo.events.append("memory_proposal_error", run_id, len(events), {"error": error})


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
        json_output: bool = typer_mod.Option(False, "--json"),
    ) -> None:
        raise typer_mod.Exit(
            goal_command(action, raw_goal, option=option, json_output=json_output)
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


def _argparse_main(argv: list[str] | None = None) -> int:
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
    goal_parser.add_argument("--json", dest="json_output", action="store_true")

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


def main(argv: list[str] | None = None) -> int:
    if _HAS_TUI and argv is None:
        if len(sys.argv) == 1 and sys.stdin.isatty():
            return repl_command()
        app()
        return 0
    return _argparse_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
