"""LoopOS CLI/FLI entry point."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from loopos.ail.codec import instruction_to_ail
from loopos.ail.models import AILInstruction
from loopos.core.isa import Instruction
from loopos.core.state import LoopState
from loopos.goal import GoalNegotiator
from loopos.gateway import ChatOpsGateway
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
from loopos.model_kernel import MultiModelScheduler, ProviderRegistry
from loopos.policy_os.audit import PolicyAuditLog
from loopos.policy_os.engine import PolicyEngine
from loopos.review import ReviewCoordinator, ReviewStore
from loopos.syscalls import create_default_syscall_router
from loopos.tasks import TaskStore
from loopos.triggers import TriggerKernel
from loopos.worktree import WorktreeManager, WorktreeStore

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


def _paths(data_dir: str | Path) -> dict[str, Path]:
    base = Path(data_dir)
    return {
        "base": base,
        "events": base / "events.jsonl",
        "runs": base / "runs",
        "skills": base / "skills.jsonl",
        "beliefs": base / "beliefs.jsonl",
        "policy_audit": base / "policy_audit.jsonl",
        "tasks": base / "tasks.json",
        "worktrees": base / "worktrees.json",
        "reviews": base / "reviews.json",
    }


def _policy_engine() -> PolicyEngine:
    return PolicyEngine.load_default()


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


def skills_command(
    action: str = "list",
    arg: str | None = None,
    *,
    data_dir: str | Path = ".loopos",
) -> int:
    repo = MemoryRepository(_paths(data_dir)["base"])
    skills = repo.skills.list()
    if action == "review":
        proposals = repo.list_skill_proposals(status="pending")
        print(json.dumps([item.model_dump(mode="json") for item in proposals], ensure_ascii=False, indent=2))
        return 0
    if action == "accept":
        if not arg:
            print("skills accept requires PROPOSAL_ID.", file=sys.stderr)
            return 1
        try:
            proposal = repo.commit_skill_proposal(arg)
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"{proposal.status}: {proposal.id}")
        return 0 if proposal.status in {"accepted", "merged"} else 1
    if action == "disable":
        if not arg:
            print("skills disable requires SKILL_ID.", file=sys.stderr)
            return 1
        for skill in skills:
            if skill.id == arg:
                skill.status = "disabled"
                repo.skills.upsert(skill)
                repo.index.upsert_skill(skill)
                print(f"disabled: {skill.id}")
                return 0
        print(f"Skill not found: {arg}", file=sys.stderr)
        return 1
    if action != "list":
        print(f"Unknown skills action: {action}", file=sys.stderr)
        return 1
    skills = [skill for skill in skills if skill.status == "active"]
    if not skills:
        print("No skills stored.")
        return 0
    print(json.dumps([skill.model_dump(mode="json") for skill in skills], ensure_ascii=False, indent=2))
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


def goal_command(
    action: str,
    raw_goal: str,
    *,
    option: str | None = None,
    json_output: bool = False,
) -> int:
    negotiator = GoalNegotiator()
    payload: Any
    if action == "analyze":
        payload = negotiator.analyze(raw_goal)
    elif action == "propose":
        payload = negotiator.propose(raw_goal)
    elif action == "finalize":
        try:
            payload = negotiator.finalize(raw_goal, option_ids=_parse_goal_options(option))
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    else:
        print(f"Unknown goal action: {action}", file=sys.stderr)
        return 1
    if json_output or action != "propose":
        print(payload.model_dump_json(indent=2))
        return 0
    for item in payload.options:
        print(f"[{item.id}] {item.title}: {item.objective}")
    return 0


def tasks_command(
    action: str = "list",
    arg: str | None = None,
    *,
    data_dir: str | Path = ".loopos",
    quick_win: bool = False,
    json_output: bool = False,
) -> int:
    store = TaskStore(_paths(data_dir)["tasks"])
    if action == "list":
        tasks = store.list()
        if json_output:
            print(json.dumps([task.model_dump(mode="json") for task in tasks], ensure_ascii=False, indent=2))
        elif not tasks:
            print("No tasks stored.")
        else:
            for task in tasks:
                marker = " quick-win" if task.quick_win else ""
                print(f"{task.id} [{task.status}] {task.title}{marker}")
        return 0
    if action == "next":
        next_task = store.next(quick_win=quick_win)
        if next_task is None:
            print("No matching task.")
            return 0
        print(next_task.model_dump_json(indent=2))
        return 0
    if action == "show":
        if not arg:
            print("tasks show requires TASK_ID.", file=sys.stderr)
            return 1
        try:
            task = store.load(arg)
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(task.model_dump_json(indent=2))
        return 0
    print(f"Unknown tasks action: {action}", file=sys.stderr)
    return 1


def triggers_command(
    action: str = "list",
    trigger_id: str | None = None,
    *,
    data_dir: str | Path = ".loopos",
) -> int:
    kernel = TriggerKernel(TaskStore(_paths(data_dir)["tasks"]))
    if action == "list":
        print(json.dumps([item.model_dump(mode="json") for item in kernel.list()], ensure_ascii=False, indent=2))
        return 0
    if action == "fire":
        if not trigger_id:
            print("triggers fire requires TRIGGER_ID.", file=sys.stderr)
            return 1
        try:
            task = kernel.fire(trigger_id)
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(task.model_dump_json(indent=2))
        return 0
    print(f"Unknown triggers action: {action}", file=sys.stderr)
    return 1


def worktrees_command(
    action: str = "list",
    task_id: str | None = None,
    *,
    data_dir: str | Path = ".loopos",
) -> int:
    paths = _paths(data_dir)
    store = WorktreeStore(paths["worktrees"])
    if action == "list":
        print(json.dumps([item.model_dump(mode="json") for item in store.list()], ensure_ascii=False, indent=2))
        return 0
    if action == "plan":
        if not task_id:
            print("worktrees plan requires TASK_ID.", file=sys.stderr)
            return 1
        try:
            task = TaskStore(paths["tasks"]).load(task_id)
            record = WorktreeManager(store).plan_for_task(task)
        except (KeyError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(record.model_dump_json(indent=2))
        return 0
    print(f"Unknown worktrees action: {action}", file=sys.stderr)
    return 1


def review_command(
    action: str = "list",
    task_id: str | None = None,
    *,
    data_dir: str | Path = ".loopos",
    producer: str = "producer",
    verifier: str = "verifier",
    reviewer: str = "reviewer",
) -> int:
    paths = _paths(data_dir)
    store = ReviewStore(paths["reviews"])
    if action == "list":
        print(json.dumps([item.model_dump(mode="json") for item in store.list()], ensure_ascii=False, indent=2))
        return 0
    if action == "start":
        if not task_id:
            print("review start requires TASK_ID.", file=sys.stderr)
            return 1
        try:
            task = TaskStore(paths["tasks"]).load(task_id)
            review = ReviewCoordinator(store).start(
                task,
                producer=producer,
                verifier=verifier,
                reviewer=reviewer,
            )
        except (KeyError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        task.review_id = review.id
        TaskStore(paths["tasks"]).save(task)
        print(review.model_dump_json(indent=2))
        return 0
    print(f"Unknown review action: {action}", file=sys.stderr)
    return 1


def providers_command(
    action: str = "list",
    value: str | None = None,
    *,
    json_output: bool = False,
) -> int:
    registry = ProviderRegistry()
    if action == "list":
        rows = [profile.model_dump(mode="json") for profile in registry.list()]
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if action == "route":
        capabilities = [item.strip() for item in (value or "text").split(",") if item.strip()]
        try:
            profile = registry.route(capabilities)  # type: ignore[arg-type]
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(profile.model_dump_json(indent=2))
        return 0
    if action == "assign":
        role = value or "primary_reasoner"
        try:
            assignment = MultiModelScheduler(registry).assign(role)  # type: ignore[arg-type]
        except (KeyError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if json_output:
            print(assignment.model_dump_json(indent=2))
        else:
            print(f"{assignment.role}: {assignment.provider_id} ({assignment.reason_code})")
        return 0
    print(f"Unknown providers action: {action}", file=sys.stderr)
    return 1


def gateway_command(
    action: str = "simulate",
    channel: str = "telegram",
    text: str = "hello",
    *,
    user_id: str = "user",
) -> int:
    gateway = ChatOpsGateway()
    if action == "simulate":
        try:
            event = gateway.receive(channel, user_id, text)  # type: ignore[arg-type]
            spec = gateway.to_run_spec(event)
        except (KeyError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(
            json.dumps(
                {
                    "event": event.model_dump(mode="json"),
                    "run_spec": spec.model_dump(mode="json"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    print(f"Unknown gateway action: {action}", file=sys.stderr)
    return 1


def memory_command(
    action: str = "list",
    arg: str | None = None,
    *,
    from_run: str | None = None,
    data_dir: str | Path = ".loopos",
    verbose: bool = False,
) -> int:
    repo = MemoryRepository(_paths(data_dir)["base"])
    if action == "list":
        items = repo.list_memory(status="active")
        if not items:
            print("No active memory.")
            return 0
        print(json.dumps([item.model_dump(mode="json") for item in items], ensure_ascii=False, indent=2))
        return 0
    if action == "search":
        if not arg:
            print("Search query is required.", file=sys.stderr)
            return 1
        items = repo.retrieve(query_text=arg, tags=arg.split(), limit=10)
        print(json.dumps([item.model_dump(mode="json") for item in items], ensure_ascii=False, indent=2))
        return 0
    if action == "propose":
        if not from_run:
            print("--from-run RUN_ID is required.", file=sys.stderr)
            return 1
        proposal = repo.proposal_for_run(from_run)
        repo.propose(proposal)
        print(f"Created proposal {proposal.id}")
        if verbose:
            print(proposal.model_dump_json(indent=2))
        return 0
    if action == "review":
        proposals = repo.list_proposals(status="pending")
        if not proposals:
            print("No pending memory proposals.")
            return 0
        print(json.dumps([proposal.model_dump(mode="json") for proposal in proposals], ensure_ascii=False, indent=2))
        return 0
    if action in {"accept", "reject"}:
        if not arg:
            print(f"Proposal id is required for memory {action}.", file=sys.stderr)
            return 1
        try:
            proposal = repo.decide_proposal(
                arg,
                "accepted" if action == "accept" else "rejected",
                reasons=[f"CLI {action}"],
            )
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"{proposal.status}: {proposal.id}")
        return 0
    if action == "reindex":
        counts = repo.reindex()
        print(json.dumps(counts, ensure_ascii=False, indent=2))
        return 0
    print(f"Unknown memory action: {action}", file=sys.stderr)
    return 1


def profile_command(
    action: str = "show",
    key: str | None = None,
    value: str | None = None,
    *,
    data_dir: str | Path = ".loopos",
) -> int:
    repo = MemoryRepository(_paths(data_dir)["base"])
    if action == "show":
        profile = repo.get_profile()
        if not profile:
            print("No user profile.")
        else:
            print(json.dumps(profile, ensure_ascii=False, indent=2))
        return 0
    if action == "set":
        if not key or value is None:
            print("profile set requires KEY and VALUE.", file=sys.stderr)
            return 1
        repo.set_profile(key, value)
        print(f"Set profile {key}")
        return 0
    print(f"Unknown profile action: {action}", file=sys.stderr)
    return 1


def policy_command(
    action: str = "list",
    policy_id: str | None = None,
    *,
    scope: str | None = None,
    input_json: str | None = None,
    data_dir: str | Path = ".loopos",
    verbose: bool = False,
    cmd: str | None = None,
) -> int:
    engine = _policy_engine()
    if action == "list":
        rows = [
            {
                "id": rule.id,
                "scope": rule.scope,
                "priority": rule.priority,
                "severity": rule.severity,
                "actions": [item.type for item in rule.actions],
            }
            for rule in engine.registry.list_rules(scope=scope)
        ]
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if action == "show":
        if not policy_id:
            print("policy show requires POLICY_ID.", file=sys.stderr)
            return 1
        try:
            try:
                payload = engine.registry.get_rule(policy_id).model_dump(mode="json")
            except KeyError:
                payload = engine.registry.get_pack(policy_id).model_dump(mode="json")
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if action == "check":
        if not scope:
            print("policy check requires --scope SCOPE.", file=sys.stderr)
            return 1
        try:
            subject = json.loads(input_json or "{}")
        except json.JSONDecodeError as exc:
            print(f"--input must be JSON: {exc}", file=sys.stderr)
            return 1
        if not isinstance(subject, dict):
            print("--input must be a JSON object.", file=sys.stderr)
            return 1
        decision = engine.evaluate(scope, subject=subject)
        if decision.audit_required:
            PolicyAuditLog(_paths(data_dir)["policy_audit"]).append(scope, subject, decision)
        print(decision.model_dump_json(indent=2))
        return 0 if decision.allowed else 2
    if action == "audit":
        rows = PolicyAuditLog(_paths(data_dir)["policy_audit"]).list()
        if not rows:
            print("No policy audit entries.")
            return 0
        print(json.dumps(rows if verbose else rows[-20:], ensure_ascii=False, indent=2))
        return 0
    if action == "explain":
        if not cmd:
            print("policy explain requires --cmd CMD.", file=sys.stderr)
            return 1
        decision = engine.evaluate(
            "terminal.execute",
            subject={"cmd": cmd, "risk_level": "medium"},
            tags=["terminal", "explain"],
            risk_level="medium",
        )
        print(decision.model_dump_json(indent=2))
        return 0 if decision.allowed else 2
    print(f"Unknown policy action: {action}", file=sys.stderr)
    return 1


def ail_command(action: str = "validate", file: str | None = None, *, verbose: bool = False) -> int:
    if action not in {"validate", "inspect"}:
        print(f"Unknown ail action: {action}", file=sys.stderr)
        return 1
    if not file:
        print(f"ail {action} requires FILE.", file=sys.stderr)
        return 1
    try:
        payload = json.loads(Path(file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not read AIL input: {exc}", file=sys.stderr)
        return 1
    try:
        instruction = AILInstruction.model_validate(payload)
    except ValidationError:
        try:
            instruction = instruction_to_ail(Instruction.model_validate(payload))
        except ValidationError as exc:
            print(f"Invalid AIL instruction: {exc}", file=sys.stderr)
            return 1
    if action == "validate":
        print(f"valid AIL instruction: {instruction.id}")
        if verbose:
            print(instruction.model_dump_json(indent=2))
        return 0
    print(instruction.model_dump_json(indent=2))
    return 0


def config_command(*, data_dir: str | Path = ".loopos") -> int:
    print(
        json.dumps(
            {
                "data_dir": str(Path(data_dir)),
                "runtime": "python",
                "kernel": "v2",
                "llm": "mock-only",
                "web_ui": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
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


def _parse_goal_options(value: str | None) -> list[int]:
    if not value:
        return []
    try:
        options = [int(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as exc:
        raise ValueError("goal options must be comma-separated integers") from exc
    if not options or any(option < 1 or option > 5 for option in options):
        raise ValueError("goal options must be between 1 and 5")
    return list(dict.fromkeys(options))


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
    ) -> None:
        raise typer_mod.Exit(
            tasks_command(
                action,
                arg,
                data_dir=data_dir,
                quick_win=quick_win,
                json_output=json_output,
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
    ) -> None:
        raise typer_mod.Exit(worktrees_command(action, task_id, data_dir=data_dir))

    @app.command("review")
    def _typer_review(
        action: str = typer_mod.Argument("list"),
        task_id: str | None = typer_mod.Argument(None),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        producer: str = typer_mod.Option("producer", "--producer"),
        verifier: str = typer_mod.Option("verifier", "--verifier"),
        reviewer: str = typer_mod.Option("reviewer", "--reviewer"),
    ) -> None:
        raise typer_mod.Exit(
            review_command(
                action,
                task_id,
                data_dir=data_dir,
                producer=producer,
                verifier=verifier,
                reviewer=reviewer,
            )
        )

    @app.command("providers")
    def _typer_providers(
        action: str = typer_mod.Argument("list"),
        value: str | None = typer_mod.Argument(None),
        json_output: bool = typer_mod.Option(False, "--json"),
    ) -> None:
        raise typer_mod.Exit(providers_command(action, value, json_output=json_output))

    @app.command("gateway")
    def _typer_gateway(
        action: str = typer_mod.Argument("simulate"),
        channel: str = typer_mod.Argument("telegram"),
        text: str = typer_mod.Argument("hello"),
        user_id: str = typer_mod.Option("user", "--user-id"),
    ) -> None:
        raise typer_mod.Exit(gateway_command(action, channel, text, user_id=user_id))

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

    triggers_parser = sub.add_parser("triggers")
    triggers_parser.add_argument("action", nargs="?", default="list")
    triggers_parser.add_argument("trigger_id", nargs="?")
    triggers_parser.add_argument("--data-dir", default=".loopos")

    worktrees_parser = sub.add_parser("worktrees")
    worktrees_parser.add_argument("action", nargs="?", default="list")
    worktrees_parser.add_argument("task_id", nargs="?")
    worktrees_parser.add_argument("--data-dir", default=".loopos")

    review_parser = sub.add_parser("review")
    review_parser.add_argument("action", nargs="?", default="list")
    review_parser.add_argument("task_id", nargs="?")
    review_parser.add_argument("--data-dir", default=".loopos")
    review_parser.add_argument("--producer", default="producer")
    review_parser.add_argument("--verifier", default="verifier")
    review_parser.add_argument("--reviewer", default="reviewer")

    providers_parser = sub.add_parser("providers")
    providers_parser.add_argument("action", nargs="?", default="list")
    providers_parser.add_argument("value", nargs="?")
    providers_parser.add_argument("--json", dest="json_output", action="store_true")

    gateway_parser = sub.add_parser("gateway")
    gateway_parser.add_argument("action", nargs="?", default="simulate")
    gateway_parser.add_argument("channel", nargs="?", default="telegram")
    gateway_parser.add_argument("text", nargs="?", default="hello")
    gateway_parser.add_argument("--user-id", default="user")

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
        )
    if args.command == "triggers":
        return triggers_command(args.action, args.trigger_id, data_dir=args.data_dir)
    if args.command == "worktrees":
        return worktrees_command(args.action, args.task_id, data_dir=args.data_dir)
    if args.command == "review":
        return review_command(
            args.action,
            args.task_id,
            data_dir=args.data_dir,
            producer=args.producer,
            verifier=args.verifier,
            reviewer=args.reviewer,
        )
    if args.command == "providers":
        return providers_command(args.action, args.value, json_output=args.json_output)
    if args.command == "gateway":
        return gateway_command(
            args.action,
            args.channel,
            args.text,
            user_id=args.user_id,
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
