"""Kernel run, status, trace, replay, and tool commands."""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path

from loopos.cli.commands.goal import parse_goal_options
from loopos.cli.context import data_paths
from loopos.cli.renderers import print_history, print_run, print_tools, print_trace
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
        option_ids = parse_goal_options(goal_option)
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
    paths = data_paths(data_dir)
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
    run = KernelLoopEngine(runtime, memory_repository=repository).run(
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
    print_run(
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
        run = RunManager(data_paths(data_dir)["runs"]).load(run_id)
    except FileNotFoundError:
        print(f"Run not found: {run_id}", file=sys.stderr)
        return 1
    print_run(run, verbose=verbose)
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
    paths = data_paths(data_dir)
    try:
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
    print_run(run, trace_store=runtime.trace_store, verbose=verbose, json_output=json_output)
    if run.status == "succeeded":
        return 0
    return 3 if run.status == "waiting_approval" else 1


def history_command(run_id: str, *, data_dir: str | Path = ".loopos") -> int:
    events = TraceStore(data_paths(data_dir)["events"]).list(run_id)
    if not events:
        print(f"No events for run: {run_id}")
        return 0
    print_history(run_id, events)
    return 0


def trace_command(
    run_id: str,
    *,
    data_dir: str | Path = ".loopos",
    show_ail: bool = False,
    show_policy: bool = False,
    json_output: bool = False,
) -> int:
    events = TraceStore(data_paths(data_dir)["events"]).list(run_id)
    if not events:
        print(f"No events for run: {run_id}", file=sys.stderr)
        return 1
    selected = events
    if show_ail and not show_policy:
        selected = [event for event in events if event.kind == "instruction"]
    elif show_policy and not show_ail:
        selected = [event for event in events if event.kind == "policy"]
    print_trace(run_id, selected, json_output=json_output)
    return 0


def replay_command(
    run_id: str,
    step: int,
    *,
    data_dir: str | Path = ".loopos",
    json_output: bool = False,
) -> int:
    paths = data_paths(data_dir)
    try:
        durable: RunRecord | None = RunManager(paths["runs"]).load(run_id)
    except FileNotFoundError:
        durable = None
    result = ReplayEngine(TraceStore(paths["events"])).replay(run_id, step, durable=durable)
    if not result.events:
        print(f"No replayable events for run {run_id} step {step}", file=sys.stderr)
        return 1
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0


def tools_command(
    action: str = "list", *, workspace: str | Path = ".", json_output: bool = False
) -> int:
    if action != "list":
        print(f"Unknown tools action: {action}", file=sys.stderr)
        return 1
    print_tools(
        create_default_syscall_router(workspace).registry.list(),
        json_output=json_output,
    )
    return 0


def repl_command() -> int:
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
