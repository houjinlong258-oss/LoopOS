"""Persistent task CLI commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from loopos.cli.context import data_paths
from loopos.i18n import t as _t
from loopos.tasks import TaskArtifactStore, TaskRecord, TaskStore


def _render_task_list_human(tasks: list[Any]) -> int:
    """Render a task list as a Rich panel.

    Falls back to a flat text printout when Rich is unavailable so
    ``tasks --human`` still produces a readable result in CI / minimal envs.
    """
    from loopos.cli._human_styles import HAS_RICH
    if not HAS_RICH:
        if not tasks:
            print("No tasks stored.")
            return 0
        for task in tasks:
            marker = " quick-win" if task.quick_win else ""
            print(f"{task.id} [{task.status}] {task.title}{marker}")
        return 0
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    console = Console()
    if not tasks:
        console.print(Panel(
            f"[dim]{_t('panel.tasks.empty')}[/dim]",
            title=f"[bold cyan]{_t('panel.tasks.list_title')}[/bold cyan] [dim]empty[/dim]",
            border_style="cyan",
        ))
        return 0
    table = Table(box=None, padding=(0, 1), show_header=True, header_style="bold cyan")
    table.add_column("id", style="cyan")
    table.add_column("status")
    table.add_column("title", style="white")
    table.add_column("type", style="dim")
    for task in tasks:
        status = task.status
        status_color = {
            "open": "yellow", "in_progress": "cyan", "blocked": "red",
            "done": "green", "completed": "green",
        }.get(status, "white")
        status_label = _t(f"task_status.{status}", default=status)
        marker = " [green](quick-win)[/green]" if task.quick_win else ""
        table.add_row(
            task.id, f"[{status_color}]{status_label}[/{status_color}]",
            task.title + marker, task.type or "?",
        )
    console.print(Panel(table, title=f"[bold cyan]{_t('panel.tasks.list_title')}[/bold cyan] "
                                      f"[cyan]{len(tasks)} item(s)[/cyan]",
                          border_style="cyan"))
    return 0


def _render_task_detail_human(payload: dict[str, Any]) -> int:
    """Render a single task dict as a Rich panel."""
    from loopos.cli._human_styles import HAS_RICH
    if not HAS_RICH:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    console = Console()
    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(width=14)
    grid.add_column()
    rows = [(k, str(v)) for k, v in payload.items()
            if not isinstance(v, (dict, list))]
    for k, v in rows:
        grid.add_row(f"[bold white]{k}[/bold white]", v)
    todos = payload.get("todos") or []
    if todos:
        todo_lines = "\n".join(f"  - {t}" for t in todos)
        grid.add_row("[bold white]todos[/bold white]", Text.from_markup(todo_lines))
    console.print(Panel(grid, title=f"[bold cyan]{payload.get('id', '?')}[/bold cyan]",
                        border_style="cyan"))
    return 0


def tasks_command(
    action: str = "list",
    arg: str | None = None,
    *,
    data_dir: str | Path = ".loopos",
    quick_win: bool = False,
    json_output: bool = False,
    human_output: bool = False,
    goal: str | None = None,
    task_type: str = "coordination",
    text: str | None = None,
    content: str | None = None,
    title: str | None = None,
    requires_worktree: bool = False,
    ready: bool = False,
) -> int:
    paths = data_paths(data_dir)
    store = TaskStore(paths["tasks"])
    artifacts = TaskArtifactStore(paths["task_artifacts"])
    # Convenience: ``tasks --human`` flips json_output off so the
    # legacy ``--json/--human`` typer flag wiring behaves as expected.
    if human_output:
        json_output = False
    if action == "list":
        tasks = store.list()
        if human_output:
            return _render_task_list_human(tasks)
        if json_output:
            print(
                json.dumps(
                    [task.model_dump(mode="json") for task in tasks],
                    ensure_ascii=False,
                    indent=2,
                )
            )
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
        payload = next_task.model_dump(mode="json")
        if human_output:
            return _render_task_detail_human(payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if action == "create":
        if not arg:
            print("tasks create requires TITLE.", file=sys.stderr)
            return 1
        try:
            task = store.create(
                TaskRecord(
                    title=arg,
                    goal=goal or arg,
                    type=task_type,  # type: ignore[arg-type]
                    quick_win=quick_win,
                    requires_worktree=requires_worktree or task_type == "code_change",
                )
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        payload = task.model_dump(mode="json")
        if human_output:
            return _render_task_detail_human(payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
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
        payload = task.model_dump(mode="json")
        if human_output:
            return _render_task_detail_human(payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if action == "todo":
        if not arg or not text:
            print("tasks todo requires TASK_ID and --text TEXT.", file=sys.stderr)
            return 1
        try:
            task = store.add_todo(arg, text)
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        payload = task.model_dump(mode="json")
        if human_output:
            return _render_task_detail_human(payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if action == "done":
        if not arg or not text:
            print("tasks done requires TASK_ID and --text TODO_ID.", file=sys.stderr)
            return 1
        try:
            task = store.complete_todo(arg, text)
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        payload = task.model_dump(mode="json")
        if human_output:
            return _render_task_detail_human(payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if action in {"report", "patch", "pr"}:
        if not arg or not content:
            print(f"tasks {action} requires TASK_ID and --content TEXT.", file=sys.stderr)
            return 1
        try:
            store.load(arg)
            artifact = artifacts.create(
                task_id=arg,
                artifact_type=action,  # type: ignore[arg-type]
                title=title or f"{action} for {arg}",
                content=content,
                ready=ready,
            )
        except (KeyError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        payload = artifact.model_dump(mode="json")
        if human_output:
            return _render_task_detail_human(payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if action == "artifacts":
        rows = artifacts.list(task_id=arg)
        if human_output:
            from loopos.cli._human_styles import HAS_RICH
            if not HAS_RICH:
                print(json.dumps([r.model_dump(mode="json") for r in rows],
                                 ensure_ascii=False, indent=2))
                return 0
            from rich.console import Console
            from rich.panel import Panel
            from rich.table import Table as _Tbl
            console = Console()
            t = _Tbl(box=None, padding=(0, 1), show_header=True,
                     header_style="bold cyan")
            t.add_column("id", style="cyan")
            t.add_column("type")
            t.add_column("title", style="white")
            t.add_column("status", style="green")
            for r in rows:
                t.add_row(r.id, str(r.type), r.title,
                          f"[green]{r.status}[/green]" if r.status == "ready"
                          else f"[dim]{r.status}[/dim]")
            console.print(Panel(t,
                title=f"[bold cyan]{_t('panel.tasks.artifacts_title')}[/bold cyan] [cyan]{len(rows)} item(s)[/cyan]",
                border_style="cyan"))
            return 0
        print(
            json.dumps(
                [item.model_dump(mode="json") for item in rows],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    print(f"Unknown tasks action: {action}", file=sys.stderr)
    return 1


__all__ = ["TaskArtifactStore", "TaskRecord", "TaskStore", "tasks_command"]
