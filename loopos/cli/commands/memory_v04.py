"""v0.4.0 closeout: ``loopos memory ...`` commands.

The memory CLI is a thin wrapper around ``loopos.project_memory``.
In the v0.4.0 closeout it exposes ``memory compile`` which builds
a role-specific ``ContextPacket`` from an in-memory store. A
real CLI would back this with a persistent project-memory store;
the closeout minimum is the typed compile pipeline.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from loopos.agent_language.roles import AgentRole
from loopos.project_memory import (
    DecisionMemory,
    FailureMemory,
    InMemoryProjectMemoryStore,
    MemoryCompiler,
    ProjectMemoryItem,
    TestMemory,
)


_ROLE_ALIASES = {
    "planner": AgentRole.PLANNER,
    "builder": AgentRole.BUILDER,
    "tester": AgentRole.TESTER,
    "reviewer": AgentRole.REVIEWER,
    "repairer": AgentRole.REPAIRER,
    "optimizer": AgentRole.OPTIMIZER,
    "deliverer": AgentRole.DELIVERY_EVALUATOR,
}


def _parse_item(d: dict[str, Any]) -> ProjectMemoryItem:
    """Dispatch to the correct ``*Memory`` subclass by ``type``."""
    t = d.get("type")
    if t == "decision":
        return DecisionMemory(**d)
    if t == "failure":
        return FailureMemory(**d)
    if t == "test":
        return TestMemory(**d)
    return ProjectMemoryItem(**d)


def memory_compile_command(
    items: str,
    target_role: str = "planner",
    goal_summary: str = "",
    current_gap: str = "",
    token_budget: int = 900,
    run_id: str | None = None,
    iteration_index: int = 0,
    json_output: bool = True,
    items_file: str | None = None,
) -> int:
    """Build a ``ContextPacket`` from a list of memory items.

    ``items`` is either a JSON string or a path to a JSON file
    containing a list of ``ProjectMemoryItem``-shaped dicts.
    """
    role = _ROLE_ALIASES.get(target_role)
    if role is None:
        print(f"unknown target role: {target_role}", file=sys.stderr)
        return 2

    if items_file:
        with open(items_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
    else:
        try:
            raw = json.loads(items)
        except json.JSONDecodeError as exc:
            print(f"invalid items JSON: {exc}", file=sys.stderr)
            return 2

    if not isinstance(raw, list):
        print("items must be a list of memory records", file=sys.stderr)
        return 2

    store = InMemoryProjectMemoryStore()
    for d in raw:
        store.add(_parse_item(d))

    compiler = MemoryCompiler(store=store)
    packet = compiler.compile(
        target_role=role,
        goal_summary=goal_summary,
        current_gap=current_gap,
        token_budget=token_budget,
        run_id=run_id,
        iteration_index=iteration_index,
    )
    if json_output:
        sys.stdout.write(json.dumps(packet.model_dump(mode="json"), indent=2, default=str))
        sys.stdout.write("\n")
    else:
        # ``--human`` panel: cyan grid summarising role / selected /
        # omitted / tokens, with the selected items table on the side.
        from loopos.cli._human_styles import HAS_RICH
        if not HAS_RICH:
            sys.stdout.write(
                f"role={packet.target_role} | selected={len(packet.selected_memory)} "
                f"| omitted={len(packet.omitted_memory_reason)} "
                f"| tokens={packet.estimated_tokens}/{packet.token_budget}\n"
            )
            return 0
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        console = Console()
        grid = Table.grid(expand=True, padding=(0, 1))
        grid.add_column(width=18)
        grid.add_column()
        grid.add_row("[bold white]role[/bold white]", f"[cyan]{packet.target_role}[/cyan]")
        grid.add_row("[bold white]selected[/bold white]", f"[green]{len(packet.selected_memory)}[/green]")
        grid.add_row("[bold white]omitted[/bold white]", f"[yellow]{len(packet.omitted_memory_reason)}[/yellow]")
        grid.add_row("[bold white]tokens[/bold white]", f"[blue]{packet.estimated_tokens}/{packet.token_budget}[/blue]")
        # Optional: list selected memory ids under the grid.
        if packet.selected_memory:
            def _summary(m: Any) -> str:
                # ProjectMemoryItem / DecisionMemory / FailureMemory
                # don't all expose a ``summary`` field; fall back to
                # content / fact / statement / expected_improvement.
                return (
                    getattr(m, "summary", None)
                    or getattr(m, "content", None)
                    or getattr(m, "fact", None)
                    or getattr(m, "statement", None)
                    or getattr(m, "expected_improvement", None)
                    or ""
                )
            inner = "\n".join(
                f"  - [cyan]{getattr(m, 'id', '?')}[/cyan] [dim]{getattr(m, 'type', '?')}[/dim] "
                f"{_summary(m)[:60]}"
                for m in packet.selected_memory[:8]
            )
            if len(packet.selected_memory) > 8:
                inner += f"\n  [dim](+{len(packet.selected_memory) - 8} more)[/dim]"
            console.print(Panel(
                grid,
                title="[bold cyan]memory compile (closeout)[/bold cyan]",
                border_style="cyan",
                subtitle=inner,
                subtitle_align="left",
            ))
            return 0
        console.print(Panel(grid,
            title="[bold cyan]memory compile (closeout)[/bold cyan]",
            border_style="cyan"))
    return 0


__all__ = ["memory_compile_command"]
