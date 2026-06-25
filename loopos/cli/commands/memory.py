"""Memory, profile, and skill CLI commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from loopos.cli.context import data_paths
from loopos.i18n import t as _t
from loopos.memory.repository import MemoryRepository
from loopos.agent_language.roles import AgentRole
from loopos.project_memory import MemoryCompiler


def _render_memory_panel(title: str, items: list[dict[str, Any]],
                         *, border_color: str = "cyan") -> int:
    """Render a list of memory records as a Rich table panel.

    ``title`` may be a raw string or a translation key (we look up
    ``title`` first against the catalog; if it starts with ``"memory."``
    we treat it as a key, otherwise as a literal title).
    """
    from loopos.cli._human_styles import HAS_RICH
    if not HAS_RICH:
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return 0
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    console = Console()
    resolved_title = _t(title) if title.startswith("panel.memory.") or title.startswith("memory.") else title
    if not items:
        console.print(Panel(
            f"[dim]{_t('panel.memory.no_items')}[/dim]",
            title=f"[bold {border_color}]{resolved_title}[/bold {border_color}]",
            border_style=border_color,
        ))
        return 0
    t = Table(box=None, padding=(0, 1), show_header=True,
              header_style="bold cyan")
    t.add_column("id", style="cyan")
    t.add_column("type")
    t.add_column("status", style="green")
    t.add_column("tags", style="dim")
    t.add_column("summary", style="white")
    for item in items:
        tags = ",".join(item.get("tags") or []) or "-"
        summary = item.get("summary") or item.get("content") or ""
        if len(summary) > 60:
            summary = summary[:57] + "..."
        status_label = _t(f"task_status.{item.get('status', '?')}", default=str(item.get("status", "?")))
        t.add_row(
            item.get("id", "?"),
            item.get("type", "?"),
            status_label,
            tags,
            summary,
        )
    console.print(Panel(t,
        title=f"[bold {border_color}]{resolved_title}[/bold {border_color}] "
              f"[{border_color}]{len(items)} item(s)[/{border_color}]",
        border_style=border_color))
    return 0


def _render_memory_counts_panel(counts: dict[str, int]) -> int:
    """Render a reindex counts payload as a 2-column grid panel."""
    from loopos.cli._human_styles import HAS_RICH
    if not HAS_RICH:
        print(json.dumps(counts, ensure_ascii=False, indent=2))
        return 0
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    console = Console()
    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(width=24)
    grid.add_column()
    for k, v in counts.items():
        grid.add_row(f"[bold white]{k}[/bold white]", f"[cyan]{v}[/cyan]")
    console.print(Panel(grid, title=f"[bold cyan]{_t('panel.memory.reindex_title')}[/bold cyan]",
                        border_style="cyan"))
    return 0


def skills_command(
    action: str = "list",
    arg: str | None = None,
    *,
    data_dir: str | Path = ".loopos",
) -> int:
    repo = MemoryRepository(data_paths(data_dir)["base"])
    skills = repo.skills.list()
    if action == "review":
        proposals = repo.list_skill_proposals(status="pending")
        print(
            json.dumps(
                [item.model_dump(mode="json") for item in proposals],
                ensure_ascii=False,
                indent=2,
            )
        )
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
    print(
        json.dumps(
            [skill.model_dump(mode="json") for skill in skills],
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def memory_command(
    action: str = "list",
    arg: str | None = None,
    *,
    from_run: str | None = None,
    data_dir: str | Path = ".loopos",
    verbose: bool = False,
    role: str | None = None,
    human_output: bool = False,
) -> int:
    repo = MemoryRepository(data_paths(data_dir)["base"])
    if action == "list":
        items = repo.list_memory(status="active")
        if human_output:
            return _render_memory_panel("panel.memory.list_title",
                                        [i.model_dump(mode="json") for i in items])
        if not items:
            print("No active memory.")
            return 0
        print(
            json.dumps(
                [item.model_dump(mode="json") for item in items],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if action == "search":
        if not arg:
            print("Search query is required.", file=sys.stderr)
            return 1
        items = repo.retrieve(query_text=arg, tags=arg.split(), limit=10)
        if human_output:
            return _render_memory_panel(f"panel.memory.search_title [{arg}]",
                                        [i.model_dump(mode="json") for i in items])
        print(
            json.dumps(
                [item.model_dump(mode="json") for item in items],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if action == "propose":
        if not from_run:
            print("--from-run RUN_ID is required.", file=sys.stderr)
            return 1
        proposal = repo.proposal_for_run(from_run)
        repo.propose(proposal)
        if human_output:
            payload = proposal.model_dump(mode="json")
            from loopos.cli._human_styles import HAS_RICH
            if not HAS_RICH:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
                return 0
            from rich.console import Console
            from rich.panel import Panel
            from rich.table import Table
            console = Console()
            grid = Table.grid(expand=True, padding=(0, 1))
            grid.add_column(width=14)
            grid.add_column()
            for k, v in payload.items():
                if isinstance(v, (dict, list)):
                    v = json.dumps(v, ensure_ascii=False, indent=2)
                grid.add_row(f"[bold white]{k}[/bold white]", str(v))
            console.print(Panel(grid,
                title=f"[bold cyan]{_t('panel.memory.propose_title')}[/bold cyan] [cyan]{payload.get('id', '?')}[/cyan]",
                border_style="cyan"))
            return 0
        print(f"Created proposal {proposal.id}")
        if verbose:
            print(proposal.model_dump_json(indent=2))
        return 0
    if action == "review":
        proposals = repo.list_proposals(status="pending")
        if human_output:
            return _render_memory_panel("panel.memory.review_title",
                                        [p.model_dump(mode="json") for p in proposals],
                                        border_color="yellow")
        if not proposals:
            print("No pending memory proposals.")
            return 0
        print(
            json.dumps(
                [proposal.model_dump(mode="json") for proposal in proposals],
                ensure_ascii=False,
                indent=2,
            )
        )
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
        if human_output:
            from loopos.cli._human_styles import HAS_RICH
            if not HAS_RICH:
                print(f"{proposal.status}: {proposal.id}")
                return 0
            from rich.console import Console
            from rich.panel import Panel
            console = Console()
            color = "green" if proposal.status == "accepted" else "red"
            console.print(Panel(
                f"[bold {color}]{proposal.status}[/bold {color}]  [cyan]{proposal.id}[/cyan]",
                title=f"[bold {color}]memory {action}[/bold {color}]",
                border_style=color))
            return 0
        print(f"{proposal.status}: {proposal.id}")
        return 0
    if action == "reindex":
        counts = repo.reindex()
        if human_output:
            return _render_memory_counts_panel(counts)
        print(json.dumps(counts, ensure_ascii=False, indent=2))
        return 0
    if action == "compile":
        target_role = AgentRole(role or arg or "repairer")
        packet = MemoryCompiler().compile(
            target_role=target_role,
            goal_summary="latest LoopOS project goal",
            current_gap="no persisted project-memory gap supplied",
            token_budget=900,
        )
        payload = packet.model_dump(mode="json")
        if human_output:
            from loopos.cli._human_styles import HAS_RICH
            if not HAS_RICH:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
                return 0
            from rich.console import Console
            from rich.panel import Panel
            from rich.table import Table
            console = Console()
            grid = Table.grid(expand=True, padding=(0, 1))
            grid.add_column(width=18)
            grid.add_column()
            grid.add_row(f"[bold white]{_t('panel.memory.role_label')}[/bold white]",
                         f"[cyan]{payload.get('target_role', '?')}[/cyan]")
            grid.add_row(f"[bold white]{_t('panel.memory.selected_label')}[/bold white]",
                         f"[green]{len(payload.get('selected_memory', []))}[/green]")
            grid.add_row(f"[bold white]{_t('panel.memory.omitted_label')}[/bold white]",
                         f"[yellow]{len(payload.get('omitted_memory_reason', []))}[/yellow]")
            grid.add_row(f"[bold white]{_t('panel.memory.tokens_label')}[/bold white]",
                         f"[blue]{payload.get('estimated_tokens', 0)}/{payload.get('token_budget', 0)}[/blue]")
            console.print(Panel(grid,
                title=f"[bold cyan]{_t('panel.memory.compile_title')}[/bold cyan]",
                border_style="cyan"))
            return 0
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if action == "failures":
        items = [
            item for item in repo.list_memory(status="active")
            if item.type == "failure" or "failure" in item.tags
        ]
        if human_output:
            return _render_memory_panel("panel.memory.failures_title",
                                        [i.model_dump(mode="json") for i in items],
                                        border_color="red")
        print(
            json.dumps(
                [item.model_dump(mode="json") for item in items],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if action == "decisions":
        items = [
            item for item in repo.list_memory(status="active")
            if item.type == "fact" and "decision" in item.tags
        ]
        if human_output:
            return _render_memory_panel("panel.memory.decisions_title",
                                        [i.model_dump(mode="json") for i in items])
        print(
            json.dumps(
                [item.model_dump(mode="json") for item in items],
                ensure_ascii=False,
                indent=2,
            )
        )
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
    repo = MemoryRepository(data_paths(data_dir)["base"])
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
