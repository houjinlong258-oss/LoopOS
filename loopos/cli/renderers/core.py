"""Kernel run, trace, and tool renderers."""

from __future__ import annotations

import json
from typing import Any, Iterable

from loopos.core.state import LoopState
from loopos.kernel import RunRecord, TraceEvent, TraceStore
from loopos.syscalls import SyscallSpec

try:  # Optional for local bootstrapping.
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    HAS_RICH = True
except Exception:  # pragma: no cover
    Console = None  # type: ignore[assignment,misc]
    Panel = None  # type: ignore[assignment,misc]
    Table = None  # type: ignore[assignment,misc]
    HAS_RICH = False


def render_state(state: LoopState, *, verbose: bool = False) -> str:
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


def render_run(run: RunRecord, *, verbose: bool = False) -> str:
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


def print_run(
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
        payload = json.loads(render_run(run, verbose=verbose))
        if show_ail:
            payload["ail"] = [event.payload for event in events if event.kind == "instruction"]
        if show_policy:
            payload["policy"] = [event.payload for event in events if event.kind == "policy"]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if not HAS_RICH:
        print(render_run(run, verbose=verbose))
        return
    console = Console()
    body = (
        f"Goal: {run.goal}\nStatus: {run.status}\nPhase: {run.phase}\n"
        f"Steps: {run.step}/{run.max_steps}\nWorkspace: {run.workspace}\nMode: {run.mode}"
    )
    console.print(Panel(body, title=f"LoopOS Kernel Run {run.run_id}"))
    for event in events:
        if event.kind == "instruction":
            console.print(f"[{event.step}/{run.max_steps}] {event.payload.get('op', 'UNKNOWN')}")
    if run.pending_approval:
        reasons = ", ".join(run.pending_approval.reason_codes)
        console.print(f"[yellow]Approval required[/yellow]: {reasons}")
    if show_ail:
        console.print_json(data=[e.payload for e in events if e.kind == "instruction"])
    if show_policy:
        console.print_json(data=[e.payload for e in events if e.kind == "policy"])


def print_history(run_id: str, events: list[TraceEvent]) -> None:
    if not HAS_RICH:
        print(json.dumps([e.model_dump(mode="json") for e in events], ensure_ascii=False, indent=2))
        return
    table = Table(title=f"History {run_id}")
    table.add_column("step")
    table.add_column("type")
    table.add_column("payload")
    for event in events:
        kind = event.type or event.kind or "run"
        table.add_row(str(event.step), kind, json.dumps(event.payload, ensure_ascii=False)[:120])
    Console().print(table)


def print_trace(run_id: str, events: list[TraceEvent], *, json_output: bool = False) -> None:
    payload = [event.model_dump(mode="json") for event in events]
    if json_output or not HAS_RICH:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    table = Table(title=f"Trace {run_id}")
    table.add_column("step")
    table.add_column("kind")
    table.add_column("summary")
    for event in events:
        summary = event.payload.get("op") or event.payload.get("summary") or event.type
        table.add_row(str(event.step), str(event.kind), str(summary)[:100])
    Console().print(table)


def print_tools(specs: Iterable[SyscallSpec], *, json_output: bool = False) -> None:
    rows = list(specs)
    payload = [spec.model_dump(mode="json") for spec in rows]
    if json_output or not HAS_RICH:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    table = Table(title="Kernel Syscalls")
    table.add_column("name")
    table.add_column("risk")
    table.add_column("policy scope")
    for spec in rows:
        table.add_row(spec.name, spec.risk, spec.policy_scope)
    Console().print(table)
