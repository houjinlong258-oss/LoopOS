"""v0.4.0 ``loopos loop ...`` commands (closeout edition).

This module is the v0.4.0 closeout version of the loop CLI. The
key change from the v0.4.0-rc version is **persistence**:

* ``loopos loop run`` generates a ``run_id``, writes the full
  ``LoopState`` and the per-iteration files to
  ``<data_dir>/runs/<run_id>/``, and prints the ``run_id`` so a
  later ``loopos loop status`` / ``loopos loop deliver`` can find
  it.
* ``loopos loop status`` and ``loopos loop deliver`` accept
  ``--run-id <id>`` and ``--latest`` and **read from disk** —
  the state survives process restarts.

The in-process ``_STATE`` holder is kept for backwards compat
but it is no longer the source of truth. The source of truth is
``<data_dir>/runs/<run_id>/``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from loopos import checkpoint_store
from loopos.checkpoint_store import (
    append_iteration,
    append_lail_signal,
    append_memory_packet,
    append_quality_score,
    init_run,
    latest_run_id,
    read_convergence_report,
    read_delivery_candidate,
    read_iterations,
    read_lail_signals,
    read_loop_state,
    run_dir,
    write_checkpoint,
    write_convergence_report,
    write_delivery_candidate,
    write_loop_state,
)
from loopos.fusion_optimizer import (
    FusionOptimizationRequest,
    FusionOptimizer,
    MadDogReviewer,
)
from loopos.lail import LailSignalBus
from loopos.loop_engine import (
    LoopEngine,
    LoopState,
)
from loopos.loop_engine.models import ProjectCheckpoint
from loopos.quality import (
    ConvergenceEngine,
    QualityScorer,
)

try:
    from rich.console import Console, Group
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.box import ROUNDED
    _HAS_RICH = True
except ImportError:  # pragma: no cover - exercised in dependency-light envs
    _HAS_RICH = False

# v0.4.0 closeout: shared --human mode utilities (mood→color, mascot,
# plain-text fallback, kv helpers). See loopos/cli/_human_styles.py.
from loopos.cli._human_styles import (
    HAS_RICH as _STYLES_HAS_RICH,  # noqa: F401 - re-export for back-compat
    MOOD_COLOR,
    emit_plain_dict,
    mood_box,
    mood_for_obj,
    xiao_huanli,
)


# The in-process holder is kept for back-compat / debugging; it
# is no longer the source of truth.
_STATE: dict[str, Any] = {"state": None, "history": []}


def _set_state(state: LoopState) -> None:
    _STATE["state"] = state
    _STATE["history"].append(state)


def _latest_state() -> LoopState | None:
    state: LoopState | None = _STATE["state"]
    return state


# ---------------------------------------------------------------------------
# Convergence / scoring helpers
# ---------------------------------------------------------------------------


def _convergence_decide(
    state: LoopState, quality: Any, findings: list[Any]
) -> Any:
    """The default ``convergence_decide`` used by ``loop_run_command``.

    The CLI demo uses ``simulated_acceptable=True`` so the v0.4.0 MVP
    can converge in the simulated path. Real deployments should use
    ``simulated_acceptable=False`` to require real evidence.
    """
    scorer = QualityScorer()
    last_it = state.iterations[-1]
    build = last_it.build_result
    tests = last_it.test_result
    if quality is not None:
        q = quality
    elif build is not None and tests is not None:
        q = scorer.score(state, build, tests, findings)
    else:
        from loopos.quality.models import QualityScore
        q = QualityScore()
    return ConvergenceEngine(simulated_acceptable=True).decide(state, q, findings)
    return ConvergenceEngine(simulated_acceptable=True).decide(state, q, findings)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _emit(obj: Any, json_output: bool) -> int:
    if json_output:
        sys.stdout.write(json.dumps(obj, indent=2, default=str))
        sys.stdout.write("\n")
        return 0
    # --human mode: render via Rich panels (v0.4.0 closeout).
    return _emit_human(obj)


def _emit_human(obj: Any) -> int:
    """Render a v0.4 result dict/list as a Rich panel for ``--human`` mode.

    The v0.4 commands return different shapes; this dispatcher picks the
    right panel. Unknown shapes fall back to a generic key-value panel.
    """
    if not _HAS_RICH:
        return emit_plain_dict(obj)

    console = Console()

    if not isinstance(obj, dict):
        if isinstance(obj, list):
            t = Table(box=ROUNDED, show_header=True, header_style="bold cyan")
            if obj and isinstance(obj[0], dict):
                cols = list(obj[0].keys())
                for c in cols:
                    t.add_column(c)
                for row in obj:
                    t.add_row(*[str(row.get(c, "")) for c in cols])
            else:
                t.add_column("value")
                for v in obj:
                    t.add_row(str(v))
            console.print(t)
            return 0
        console.print(str(obj))
        return 0

    # Shape: loop run output (has 'iterations' + 'delivery' keys)
    if "iterations" in obj and ("current_status" in obj or "delivery" in obj):
        return _emit_human_run(obj, console)

    # Shape: loop status output (has 'last_iteration' or 'lail_signals')
    if "lail_signals" in obj or "last_iteration" in obj or "checkpoint_path" in obj:
        return _emit_human_status(obj, console)

    # Shape: loop deliver output (has 'delivery_status' or 'success_criteria_coverage')
    if "delivery_status" in obj or "success_criteria_coverage" in obj or "why" in obj:
        return _emit_human_deliver(obj, console)

    # Shape: loop review output (has 'findings' or 'mad_dog_findings')
    if "findings" in obj or "mad_dog_findings" in obj:
        return _emit_human_review(obj, console)

    # Shape: loop repair output (RepairPlan or 'no_repair_plan' status)
    if "steps" in obj and ("source_findings" in obj or "priority" in obj):
        return _emit_human_repair(obj, console)
    if obj.get("status") == "no_repair_plan":
        return _emit_human_repair(obj, console)

    # Shape: loop optimize output (FusionOptimizationResult dict)
    if "recommended_next_plan" in obj or "rationale" in obj:
        return _emit_human_optimize(obj, console)

    # Generic: flat key-value panel
    return _emit_human_generic(obj, console)


def _xiao_huanli(mood: str) -> Any:
    """Compact Xiao Huanli (the raccoon mascot) for ``--human`` panels.

    4 lines, ASCII-compatible. Mood: calm / running / blocked / halted.
    Delegates to :func:`loopos.cli._human_styles.xiao_huanli` so all
    --human panels share one canonical face.
    """
    return xiao_huanli(mood)


def _mood_for_obj(obj: dict[str, Any]) -> str:
    """Pick a mood based on the v0.4 result object's status field.

    Delegates to :func:`loopos.cli._human_styles.mood_for_obj`.
    """
    return mood_for_obj(obj)


def _emit_human_run(obj: dict[str, Any], console: Any) -> int:
    """Render a ``loop run`` result as a Rich panel."""
    mood = _mood_for_obj(obj)
    cat = _xiao_huanli(mood)
    mood_color = MOOD_COLOR[mood]
    box = mood_box(mood)

    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(width=12)
    grid.add_column()

    # Run id and run_id get cyan; status/delivery get mood_color.
    # Plain values (user_goal, Iterations, Known limits) get cyan/blue so
    # they don't render as washed-out white next to the mood-coloured fields.
    rows: list[tuple[str, str]] = [
        ("Run",          f"[cyan]{obj.get('run_id', '?')}[/cyan]"),
        ("Status",       f"[{mood_color}]{obj.get('current_status', '?')}[/{mood_color}]"),
        ("Iterations",   f"[blue]{len(obj.get('iterations', []))}[/blue]"),
    ]
    if obj.get("user_goal"):
        rows.insert(1, ("User goal", f"[cyan]{obj['user_goal']}[/cyan]"))
    delivery = obj.get("delivery") or {}
    if delivery:
        rows.append(("Delivery", f"[{mood_color}]{delivery.get('status', '?')}[/{mood_color}]"))
        if delivery.get("known_limitations"):
            limits = ", ".join(
                f"[yellow]{x}[/yellow]" for x in delivery["known_limitations"]
            )
            rows.append(("Known limits", limits))

    for k, v in rows:
        grid.add_row(f"[bold white]{k}[/bold white]", v)

    last = (obj.get("iterations") or [{}])[-1]
    inner_rows: list[str] = []
    if last.get("plan"):
        plan = last["plan"]
        inner_rows.append(
            f"[bold]Last plan[/bold]: [cyan]{plan.get('title', '?')}[/cyan] "
            f"(source=[magenta]{plan.get('source', '?')}[/magenta])"
        )
    if last.get("build_result"):
        b = last["build_result"]
        inner_rows.append(
            f"[bold]Build[/bold]: [{mood_color}]{b.get('status', '?')}[/{mood_color}] "
            f"source=[dim]{b.get('source', '?')}[/dim]"
        )
    if last.get("test_result"):
        t = last["test_result"]
        passed = int(t.get("passed", 0))
        failed = int(t.get("failed", 0))
        passed_str = f"[green]{passed}[/green]" if passed else f"[dim]{passed}[/dim]"
        failed_str = f"[red]{failed}[/red]" if failed else f"[dim]{failed}[/dim]"
        inner_rows.append(
            f"[bold]Test[/bold]: [{mood_color}]{t.get('status', '?')}[/{mood_color}] "
            f"passed={passed_str} failed={failed_str}"
        )
    if last.get("quality_score"):
        q = last["quality_score"]
        inner_rows.append(
            f"[bold]Quality[/bold]: [green]{q.get('overall', '?')}[/green]"
        )
    if last.get("convergence"):
        c = last["convergence"]
        fake_n = len(c.get("fake_convergence") or [])
        fake_str = f"[red]{fake_n}[/red]" if fake_n else "[dim]0[/dim]"
        inner_rows.append(
            f"[bold]Convergence[/bold]: [cyan]{c.get('status', '?')}[/cyan]"
            f"  fake_convergence={fake_str}"
        )
    inner = "\n".join(inner_rows) if inner_rows else "[dim]no iteration details[/dim]"

    body = Group(cat, Text(""), grid, Text(""), Text.from_markup(inner))
    title = f"[bold {mood_color}]loop run · {obj.get('run_id', '?')}[/bold {mood_color}] [{mood_color}]{obj.get('current_status', '?')}[/{mood_color}]"
    console.print(Panel(body, title=title, border_style=mood_color, box=box))
    return 0


def _emit_human_status(obj: dict[str, Any], console: Any) -> int:
    """Render a ``loop status`` result as a Rich panel."""
    mood = _mood_for_obj(obj)
    cat = _xiao_huanli(mood)
    mood_color = MOOD_COLOR[mood]
    box = mood_box(mood)

    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(width=18)
    grid.add_column()
    rows: list[tuple[str, str]] = [
        ("Run",               f"[cyan]{obj.get('run_id', '?')}[/cyan]"),
        ("User goal",         f"[cyan]{obj.get('user_goal', '?')}[/cyan]"),
        ("Current status",    f"[{mood_color}]{obj.get('current_status', '?')}[/{mood_color}]"),
        ("Current iteration", f"[blue]{obj.get('current_iteration', '?')}[/blue]"),
        ("Checkpoint path",   f"[cyan]{obj.get('checkpoint_path', '?')}[/cyan]"),
    ]
    if obj.get("lail_kind_summary"):
        kinds = obj["lail_kind_summary"]
        rows.append(("LAIL kinds",
                     "  ".join(f"[cyan]{k}[/cyan]=[magenta]{v}[/magenta]" for k, v in kinds.items())))
    if obj.get("last_quality_score") or obj.get("quality_score"):
        q = obj.get("last_quality_score") or obj.get("quality_score") or {}
        rows.append(("Last quality",
                     f"overall=[green]{q.get('overall', '?')}[/green] "
                     f"goal=[green]{q.get('goal_alignment', '?')}[/green] "
                     f"test=[green]{q.get('test_health', '?')}[/green] "
                     f"delivery=[green]{q.get('delivery_readiness', '?')}[/green]"))
    if obj.get("last_loss") or obj.get("loss"):
        loss = obj.get("last_loss") or obj.get("loss") or {}
        rows.append(("Last loss",
                     f"total=[yellow]{loss.get('total', '?')}[/yellow] "
                     f"unsat=[yellow]{loss.get('unsat_required', '?')}[/yellow] "
                     f"blocking=[yellow]{loss.get('blocking_findings', '?')}[/yellow]"))
    if obj.get("convergence"):
        c = obj["convergence"]
        rows.append(("Convergence",
                     f"status=[cyan]{c.get('status', '?')}[/cyan] "
                     f"fake=[{mood_color}]{len(c.get('fake_convergence') or [])}[/{mood_color}]"))
    # v0.4.0 closeout: surface reason_codes / fake_convergence_findings as
    # visible diagnostic rows (previously only available in JSON).
    if obj.get("reason_codes"):
        codes = ", ".join(f"[red]{c}[/red]" for c in obj["reason_codes"])
        rows.append(("Reason codes", codes))
    if obj.get("fake_convergence_findings"):
        # fake-convergence findings are blocking diagnostic signals.
        findings = obj["fake_convergence_findings"]
        if isinstance(findings, list) and findings:
            preview = findings[:3]
            lines = "  ".join(f"[red]{f}[/red]" for f in preview)
            if len(findings) > 3:
                lines += f"  [dim](+{len(findings) - 3} more)[/dim]"
            rows.append(("Fake-convergence", lines))
    if obj.get("blocking_findings"):
        bf = obj["blocking_findings"]
        if isinstance(bf, list) and bf:
            preview = bf[:3]
            lines = "  ".join(f"[red]{f}[/red]" for f in preview)
            if len(bf) > 3:
                lines += f"  [dim](+{len(bf) - 3} more)[/dim]"
            rows.append(("Blocking findings", lines))
    if obj.get("next_recommended_action"):
        rows.append(("Next action", f"[cyan]{obj['next_recommended_action']}[/cyan]"))

    for k, v in rows:
        grid.add_row(f"[bold white]{k}[/bold white]", v)

    note = "[dim]this process is a fresh Python interpreter — no in-process state[/dim]"
    body = Group(cat, Text(""), grid, Text(""), Text.from_markup(note))
    title = f"[bold {mood_color}]loop status --latest[/bold {mood_color}] [{mood_color}]{obj.get('current_status', '?')}[/{mood_color}]"
    console.print(Panel(body, title=title, border_style=mood_color, box=box))
    return 0


def _emit_human_deliver(obj: dict[str, Any], console: Any) -> int:
    """Render a ``loop deliver`` result as a Rich panel."""
    ready = bool(obj.get("ready"))
    mood = "calm" if ready else ("blocked" if obj.get("fake_convergence_findings") else "halted")
    cat = _xiao_huanli(mood)
    mood_color = MOOD_COLOR[mood]
    box = mood_box(mood)

    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(width=18)
    grid.add_column()
    rows: list[tuple[str, str]] = [
        ("Run",            f"[cyan]{obj.get('run_id', '?')}[/cyan]"),
        ("User goal",      f"[cyan]{obj.get('user_goal', '?')}[/cyan]"),
        ("Delivery status", f"[{mood_color}]{obj.get('delivery_status', '?')}[/{mood_color}]"),
        ("Ready",          f"[{mood_color}]{obj.get('ready', '?')}[/{mood_color}]"),
        ("Why",            f"[cyan]{obj.get('why', '?') or '?'}[/cyan]"),
    ]
    cov = obj.get("success_criteria_coverage") or {}
    if cov:
        rows.append(("Coverage",
                     f"required=[magenta]{cov.get('required', 0)}[/magenta] "
                     f"satisfied=[green]{cov.get('satisfied', 0)}[/green] "
                     f"unsatisfied=[red]{cov.get('unsatisfied', 0)}[/red]"))
    if obj.get("quality_score"):
        q = obj["quality_score"]
        rows.append(("Quality",
                     f"overall=[green]{q.get('overall', '?')}[/green] "
                     f"goal=[green]{q.get('goal_alignment', '?')}[/green] "
                     f"test=[green]{q.get('test_health', '?')}[/green]"))
    if obj.get("convergence_status"):
        rows.append(("Convergence", f"[cyan]{obj['convergence_status']}[/cyan]"))
    if obj.get("iterations") is not None:
        rows.append(("Iterations", f"[blue]{obj['iterations']}[/blue]"))
    if obj.get("known_limitations"):
        rows.append(("Known limits", "  ".join(f"[yellow]{x}[/yellow]" for x in obj["known_limitations"])))
    if obj.get("recommended_next_loop"):
        rows.append(("Next loop", f"[cyan]{obj['recommended_next_loop']}[/cyan]"))

    for k, v in rows:
        grid.add_row(f"[bold white]{k}[/bold white]", v)

    body = Group(cat, Text(""), grid)
    title = f"[bold {mood_color}]loop deliver --latest[/bold {mood_color}] [{mood_color}]{obj.get('delivery_status', '?')}[/{mood_color}]"
    console.print(Panel(body, title=title, border_style=mood_color, box=box))
    return 0


def _emit_human_review(obj: dict[str, Any], console: Any) -> int:
    """Render a ``loop review`` result as a Rich panel.

    Shape::

        {
          "run_id": str,
          "iteration": int | None,
          "findings": list[dict],       # review findings
          "mad_dog_findings": list | None,  # optional mad-dog findings
        }
    """
    findings = obj.get("findings") or []
    mad_dog = obj.get("mad_dog_findings") or []
    has_blocking = any(
        isinstance(f, dict) and (
            f.get("severity") in {"high", "critical", "blocking"}
            or f.get("blocking") is True
        )
        for f in (findings + mad_dog)
    )
    mood = "blocked" if has_blocking else ("calm" if not findings else "halted")
    cat = _xiao_huanli(mood)
    mood_color = MOOD_COLOR[mood]
    box = mood_box(mood)

    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(width=18)
    grid.add_column()
    rows: list[tuple[str, str]] = [
        ("Run",       f"[cyan]{obj.get('run_id', '?')}[/cyan]"),
        ("Iteration", f"[blue]{obj.get('iteration', '?')}[/blue]"),
        ("Findings",  f"[{mood_color}]{len(findings)}[/{mood_color}]"),
        ("Mad-dog",   f"[{mood_color}]{len(mad_dog)}[/{mood_color}]"),
    ]
    for k, v in rows:
        grid.add_row(f"[bold white]{k}[/bold white]", v)

    finding_lines: list[str] = []
    for f in findings[:8]:
        if not isinstance(f, dict):
            finding_lines.append(f"  - [dim]{f}[/dim]")
            continue
        sev = str(f.get("severity") or "info").lower()
        sev_color = {"high": "red", "critical": "red", "blocking": "red",
                     "medium": "yellow", "warning": "yellow",
                     "low": "blue"}.get(sev, "cyan")
        target = f.get("target") or f.get("id") or "?"
        msg = f.get("message") or f.get("summary") or ""
        finding_lines.append(
            f"  - [{sev_color}]{sev}[/{sev_color}] [cyan]{target}[/cyan] {msg}"
        )
    if len(findings) > 8:
        finding_lines.append(f"  [dim](+{len(findings) - 8} more findings)[/dim]")
    if not finding_lines:
        finding_lines.append("  [dim]no findings[/dim]")

    if mad_dog:
        finding_lines.append("[bold]Mad-dog review[/bold]")
        for m in mad_dog[:5]:
            if not isinstance(m, dict):
                finding_lines.append(f"  - [dim]{m}[/dim]")
                continue
            cat_m = m.get("category") or m.get("kind") or "?"
            sev = str(m.get("severity") or "info").lower()
            sev_color = {"high": "red", "critical": "red"}.get(sev, "yellow")
            msg = m.get("message") or m.get("summary") or ""
            finding_lines.append(
                f"  - [{sev_color}]{sev}[/{sev_color}] [magenta]{cat_m}[/magenta] {msg}"
            )
        if len(mad_dog) > 5:
            finding_lines.append(f"  [dim](+{len(mad_dog) - 5} more)[/dim]")

    inner = "\n".join(finding_lines)
    body = Group(cat, Text(""), grid, Text(""), Text.from_markup(inner))
    title = f"[bold {mood_color}]loop review[/bold {mood_color}] [{mood_color}]{len(findings)} findings[/{mood_color}]"
    console.print(Panel(body, title=title, border_style=mood_color, box=box))
    return 0


def _emit_human_repair(obj: dict[str, Any], console: Any) -> int:
    """Render a ``loop repair`` result.

    Two shapes arrive here:
      * ``{"status": "no_repair_plan", ...}`` — there's no plan to show.
      * ``RepairPlan`` dict with ``steps`` / ``source_findings`` / ``priority``.
    """
    if obj.get("status") == "no_repair_plan":
        cat = _xiao_huanli("halted")
        mood_color = MOOD_COLOR["halted"]
        box = mood_box("halted")
        grid = Table.grid(expand=True, padding=(0, 1))
        grid.add_column(width=18)
        grid.add_column()
        rows = [
            ("Run",       f"[cyan]{obj.get('run_id', '?')}[/cyan]"),
            ("Iteration", f"[blue]{obj.get('iteration', '?')}[/blue]"),
            ("Status",    "[yellow]no_repair_plan[/yellow]"),
        ]
        for k, v in rows:
            grid.add_row(f"[bold white]{k}[/bold white]", v)
        body = Group(cat, Text(""), grid, Text(""),
                     Text.from_markup("[dim]no repair plan produced for this iteration[/dim]"))
        title = "[bold yellow]loop repair[/bold yellow] [yellow]no plan[/yellow]"
        console.print(Panel(body, title=title, border_style=mood_color, box=box))
        return 0

    priority = str(obj.get("priority", "medium")).lower()
    mood = "blocked" if priority in {"high", "critical"} else "halted"
    cat = _xiao_huanli(mood)
    mood_color = MOOD_COLOR[mood]
    box = mood_box(mood)

    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(width=18)
    grid.add_column()
    rows = [
        ("Plan id",      f"[cyan]{obj.get('id', '?')}[/cyan]"),
        ("Priority",     f"[{mood_color}]{priority}[/{mood_color}]"),
        ("Source count", f"[blue]{len(obj.get('source_findings') or [])}[/blue]"),
        ("Steps",        f"[blue]{len(obj.get('steps') or [])}[/blue]"),
        ("Tests to run", f"[blue]{len(obj.get('tests_to_run') or [])}[/blue]"),
    ]
    if obj.get("expected_fix"):
        rows.append(("Expected fix", f"[cyan]{obj['expected_fix']}[/cyan]"))
    for k, v in rows:
        grid.add_row(f"[bold white]{k}[/bold white]", v)

    inner_lines: list[str] = []
    if obj.get("source_findings"):
        inner_lines.append("[bold]Source findings[/bold]")
        for s in obj["source_findings"][:5]:
            inner_lines.append(f"  - [red]{s}[/red]")
        if len(obj["source_findings"]) > 5:
            inner_lines.append(f"  [dim](+{len(obj['source_findings']) - 5} more)[/dim]")
    if obj.get("steps"):
        inner_lines.append("[bold]Steps[/bold]")
        for i, s in enumerate(obj["steps"][:8], 1):
            inner_lines.append(f"  [blue]{i}.[/blue] {s}")
        if len(obj["steps"]) > 8:
            inner_lines.append(f"  [dim](+{len(obj['steps']) - 8} more)[/dim]")
    if obj.get("tests_to_run"):
        inner_lines.append("[bold]Tests to run[/bold]")
        for t in obj["tests_to_run"][:8]:
            inner_lines.append(f"  - [magenta]{t}[/magenta]")
        if len(obj["tests_to_run"]) > 8:
            inner_lines.append(f"  [dim](+{len(obj['tests_to_run']) - 8} more)[/dim]")
    inner = "\n".join(inner_lines) if inner_lines else "[dim]no steps[/dim]"
    body = Group(cat, Text(""), grid, Text(""), Text.from_markup(inner))
    title = f"[bold {mood_color}]loop repair[/bold {mood_color}] [{mood_color}]{priority}[/{mood_color}]"
    console.print(Panel(body, title=title, border_style=mood_color, box=box))
    return 0


def _emit_human_optimize(obj: dict[str, Any], console: Any) -> int:
    """Render a ``loop optimize`` result (FusionOptimizationResult dict)."""
    confidence = float(obj.get("confidence", 0.0))
    if confidence >= 0.75:
        mood = "calm"
    elif confidence >= 0.5:
        mood = "running"
    else:
        mood = "halted"
    cat = _xiao_huanli(mood)
    mood_color = MOOD_COLOR[mood]
    box = mood_box(mood)

    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(width=18)
    grid.add_column()
    rows = [
        ("Result id",    f"[cyan]{obj.get('id', '?')}[/cyan]"),
        ("Mode",         f"[cyan]{obj.get('mode', '?')}[/cyan]"),
        ("Confidence",   (f"[green]{confidence:.2f}[/green]" if confidence >= 0.75
                           else f"[yellow]{confidence:.2f}[/yellow]" if confidence >= 0.5
                           else f"[red]{confidence:.2f}[/red]")),
        ("Alternatives", f"[blue]{len(obj.get('alternatives') or [])}[/blue]"),
        ("Findings",     f"[{mood_color}]{len(obj.get('review_findings') or [])}[/{mood_color}]"),
    ]
    has_repair = obj.get("repair_plan") is not None
    has_opt = obj.get("optimization_plan") is not None
    rows.append(("Has repair plan",   "[green]yes[/green]" if has_repair else "[dim]no[/dim]"))
    rows.append(("Has optimization",  "[green]yes[/green]" if has_opt   else "[dim]no[/dim]"))
    for k, v in rows:
        grid.add_row(f"[bold white]{k}[/bold white]", v)

    inner_lines: list[str] = []
    plan = obj.get("recommended_next_plan") or {}
    if plan:
        title_p = plan.get("title") or "?"
        source_p = plan.get("source") or "?"
        inner_lines.append(
            f"[bold]Recommended plan[/bold]: [cyan]{title_p}[/cyan] "
            f"(source=[magenta]{source_p}[/magenta])"
        )
    if obj.get("rationale"):
        inner_lines.append(f"[bold]Rationale[/bold]: [cyan]{obj['rationale']}[/cyan]")
    if obj.get("disagreements"):
        inner_lines.append("[bold]Disagreements[/bold]")
        for d in obj["disagreements"][:5]:
            inner_lines.append(f"  - [yellow]{d}[/yellow]")
    if obj.get("review_findings"):
        inner_lines.append("[bold]Findings[/bold]")
        for f in obj["review_findings"][:5]:
            if not isinstance(f, dict):
                inner_lines.append(f"  - [red]{f}[/red]")
                continue
            sev = str(f.get("severity") or "info").lower()
            sev_color = {"high": "red", "critical": "red"}.get(sev, "yellow")
            msg = f.get("message") or f.get("summary") or str(f)
            target = f.get("target") or "?"
            inner_lines.append(
                f"  - [{sev_color}]{sev}[/{sev_color}] [cyan]{target}[/cyan] {msg}"
            )
        if len(obj["review_findings"]) > 5:
            inner_lines.append(f"  [dim](+{len(obj['review_findings']) - 5} more)[/dim]")
    inner = "\n".join(inner_lines) if inner_lines else "[dim]no detail[/dim]"
    body = Group(cat, Text(""), grid, Text(""), Text.from_markup(inner))
    title = (f"[bold {mood_color}]loop optimize[/bold {mood_color}] "
             f"[{mood_color}]confidence={confidence:.2f}[/{mood_color}]")
    console.print(Panel(body, title=title, border_style=mood_color, box=box))
    return 0


def _emit_human_generic(obj: dict[str, Any], console: Any) -> int:
    """Render any unknown dict as a flat key-value panel.

    v0.4.0 closeout: previously hardcoded a ``"loop ok"`` title with a
    green border for *every* unmatched payload — including blocked /
    halted results — which was misleading. We now derive a mood + title
    from the payload's status fields so unknown shapes still get an
    honest read-out.
    """
    mood = _mood_for_obj(obj)
    cat = _xiao_huanli(mood)
    mood_color = MOOD_COLOR[mood]
    box = mood_box(mood)

    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(width=22)
    grid.add_column()
    for k, v in obj.items():
        if isinstance(v, (dict, list)):
            v = json.dumps(v, default=str, indent=2)
        grid.add_row(f"[bold white]{k}[/bold white]", str(v))
    body = Group(cat, Text(""), grid)
    title = f"[bold {mood_color}]loop result[/bold {mood_color}] [{mood_color}]{mood}[/{mood_color}]"
    console.print(Panel(body, title=title, border_style=mood_color, box=box))
    return 0


def _dump_iteration(iteration: Any) -> dict[str, Any]:
    result: dict[str, Any] = iteration.model_dump(mode="json")
    return result


def _state_to_dict(state: LoopState) -> dict[str, Any]:
    base: dict[str, Any] = state.model_dump(mode="json", exclude={"iterations"})
    base["iterations"] = [_dump_iteration(it) for it in state.iterations]
    return base


# ---------------------------------------------------------------------------
# Iteration -> on-disk writes
# ---------------------------------------------------------------------------


def _persist_iteration(
    run_id: str,
    iteration: Any,
    lail_bus: LailSignalBus,
    data_dir: Path | None,
) -> None:
    """Write one iteration's records to disk.

    The function appends to:

    * ``iterations.jsonl`` (the full iteration dump)
    * ``lail_signals.jsonl`` (drained from the LAIL bus)
    * ``quality_scores.jsonl`` (the per-iteration ``QualityScore``)
    """
    dump = _dump_iteration(iteration)
    append_iteration(run_id, dump, data_dir)
    for sig in lail_bus.drain():
        append_lail_signal(run_id, sig.model_dump(mode="json"), data_dir)
    if iteration.quality_score is not None:
        append_quality_score(
            run_id, iteration.quality_score.model_dump(mode="json"), data_dir
        )


def _persist_memory_packets(
    run_id: str,
    packets: list[Any],
    data_dir: Path | None,
) -> None:
    for p in packets:
        append_memory_packet(
            run_id, p.model_dump(mode="json"), data_dir
        )


# ---------------------------------------------------------------------------
# Run command
# ---------------------------------------------------------------------------


def loop_run_command(
    goal: str,
    max_iterations: int = 3,
    dry_run: bool = True,
    json_output: bool = True,
    run_id: str | None = None,
    data_dir: str | None = None,
) -> int:
    """Drive the loop. Persists to ``<data_dir>/runs/<run_id>/``."""
    dd = Path(data_dir) if data_dir else None

    if run_id is None:
        run_id, _ = init_run(None, data_dir=dd)
    else:
        # Re-running an existing run keeps the same id; the run
        # directory is created (or reused) with a fresh created_at
        # marker only if it does not yet exist.
        run_id, _ = init_run(run_id, data_dir=dd)

    engine = LoopEngine()
    lail_bus = LailSignalBus()
    memory_packets: list[Any] = []

    # Build a state, then run the loop manually so we can drain the
    # LAIL bus per iteration.
    from loopos.loop_engine.goal import GoalEngine

    goal_engine = GoalEngine()
    user_goal = goal_engine.normalize(goal)
    success_criteria = goal_engine.generate_criteria(user_goal)
    state = LoopState(
        goal=user_goal,
        success_criteria=success_criteria,
        max_iterations=max(1, int(max_iterations)),
        trace_id=run_id,
    )
    lail_bus.make(
        "iteration_started", run_id=run_id, iteration_index=0,
        trace_id=run_id, payload={"phase": "loop_start", "goal": goal},
    )

    for index in range(state.max_iterations):
        state.current_status = "running"
        iteration = engine._drive_iteration(state, index, dry_run)
        state.iterations.append(iteration)
        iteration.quality_score = engine._scorer.score(
            state,
            iteration.build_result,
            iteration.test_result,
            iteration.review_findings,
        ) if iteration.build_result and iteration.test_result else None
        # loss + signals
        from loopos.quality.convergence import ConvergenceEngine as _CE
        ce = _CE()
        iteration.loss = ce.compute_loss(
            state, iteration.quality_score, iteration.review_findings,
        )
        from loopos.loop_engine.models import EvaluationSignal
        iteration.signals = [
            EvaluationSignal(
                id=f"sig_{f.id}",
                source="mad_dog" if f.source == "mad_dog" else "reviewer",
                category=f.category,
                severity=f.severity,
                claim=f.claim,
                evidence=list(f.evidence),
                proposed_step=f.recommended_fix,
                targets_loss_dim=(
                    "blocking_findings" if f.blocks_delivery else "unsat_required"
                ),
            )
            for f in iteration.review_findings
        ]
        # LAIL signals for this iteration
        lail_bus.make(
            "plan_emitted", run_id=run_id, iteration_index=iteration.index,
            trace_id=run_id, payload={"plan_id": iteration.plan.id, "source": iteration.plan.source},
        )
        lail_bus.make(
            "build_completed", run_id=run_id, iteration_index=iteration.index,
            trace_id=run_id, payload={"status": iteration.build_result.status if iteration.build_result else "n/a"},
        )
        lail_bus.make(
            "test_completed", run_id=run_id, iteration_index=iteration.index,
            trace_id=run_id, payload={
                "status": iteration.test_result.status if iteration.test_result else "n/a",
                "failed": iteration.test_result.failed if iteration.test_result else 0,
            },
        )
        lail_bus.make(
            "review_completed", run_id=run_id, iteration_index=iteration.index,
            trace_id=run_id, payload={"finding_count": len(iteration.review_findings)},
        )
        if iteration.repair_plan:
            lail_bus.make(
                "repair_planned", run_id=run_id, iteration_index=iteration.index,
                trace_id=run_id, payload={"priority": iteration.repair_plan.priority},
            )
        if iteration.optimization_plan:
            lail_bus.make(
                "optimization_planned", run_id=run_id, iteration_index=iteration.index,
                trace_id=run_id, payload={"target": iteration.optimization_plan.target},
            )

        # Convergence (set on the iteration before persisting so
        # the on-disk record includes the convergence decision).
        status = _convergence_decide(
            state, iteration.quality_score, iteration.review_findings,
        )
        iteration.convergence = status
        lail_bus.make(
            "convergence_decided", run_id=run_id, iteration_index=iteration.index,
            trace_id=run_id, payload={"status": status.status, "fake": len(status.fake_convergence)},
        )
        # Persist this iteration (now with convergence attached).
        _persist_iteration(run_id, iteration, lail_bus, dd)
        # Persist the convergence report
        write_convergence_report(run_id, status.model_dump(mode="json"), dd)
        # Persist the latest checkpoint
        ckpt = ProjectCheckpoint.from_iteration(state.goal.id, iteration)
        write_checkpoint(run_id, ckpt.model_dump(mode="json"), dd)
        lail_bus.make(
            "checkpoint_saved", run_id=run_id, iteration_index=iteration.index,
            trace_id=run_id, payload={"checkpoint_id": ckpt.id},
        )
        if status.status in {"deliver", "blocked", "iteration_budget_exhausted"}:
            if status.status == "deliver":
                state.current_status = "ready_to_deliver"
            elif status.status == "blocked":
                state.current_status = "blocked"
            else:
                state.current_status = "failed"
            # Drain remaining LAIL signals before break
            for sig in lail_bus.drain():
                append_lail_signal(run_id, sig.model_dump(mode="json"), dd)
            break
    else:
        # No early break; the loop ran all iterations and the
        # caller did not deliver. Mark as initialized.
        if state.current_status == "running":
            state.current_status = "initialized"

    # Final writes
    _persist_memory_packets(run_id, memory_packets, dd)
    write_loop_state(run_id, _state_to_dict(state), dd)

    # Delivery candidate
    from loopos.quality import DeliveryEngine as _DE
    cand = _DE().evaluate(state)
    write_delivery_candidate(run_id, cand.model_dump(mode="json"), dd)

    _set_state(state)

    out = {
        "run_id": run_id,
        "data_dir": str(dd or checkpoint_store.default_data_dir()),
        "current_status": state.current_status,
        "iterations": [_dump_iteration(it) for it in state.iterations],
        "delivery": cand.model_dump(mode="json"),
    }
    return _emit(out, json_output)


# ---------------------------------------------------------------------------
# Status command
# ---------------------------------------------------------------------------


def _select_run_id(run_id: str | None, data_dir: Path | None) -> str | None:
    if run_id == "latest" or run_id is None:
        return latest_run_id(data_dir)
    return run_id


def loop_status_command(
    run_id: str | None = None,
    json_output: bool = True,
    data_dir: str | None = None,
) -> int:
    """Show the run state, including the rich project-training surface.

    Accepts ``--run-id <id>`` or ``--latest`` (default). The state is
    read from disk so the call works in a fresh process.
    """
    dd = Path(data_dir) if data_dir else None
    rid = _select_run_id(run_id, dd)
    if rid is None:
        return _emit(
            {"status": "no_run", "message": "Run `loopos loop run <goal>` first."},
            json_output,
        )
    state = read_loop_state(rid, dd)
    if state is None:
        return _emit(
            {"status": "no_run", "run_id": rid,
             "message": f"No loop_state.json for run_id={rid}"},
            json_output,
        )

    iterations = read_iterations(rid, dd)
    lail = read_lail_signals(rid, dd)
    last_iter = iterations[-1] if iterations else None
    last_findings = (last_iter or {}).get("review_findings", [])
    last_failed = [
        t for t in ((last_iter or {}).get("test_result", {}) or {}).get("failures", [])
    ]
    last_repair = (last_iter or {}).get("repair_plan")
    last_opt = (last_iter or {}).get("optimization_plan")
    last_loss = (last_iter or {}).get("loss")
    last_signals = (last_iter or {}).get("signals", [])
    last_conv = (last_iter or {}).get("convergence") or {}
    last_qs = (last_iter or {}).get("quality_score")
    goal_gap = (last_loss or {}).get("goal_gap", {})

    out = {
        "run_id": rid,
        "data_dir": str(dd or checkpoint_store.default_data_dir()),
        "user_goal": state.get("goal", {}).get("raw_goal", ""),
        "current_status": state.get("current_status"),
        "current_iteration": len(iterations),
        "iterations": iterations,
        "lail_signals": lail,
        "lail_kind_summary": _lail_kind_summary(lail),
        "last_iteration": {
            "index": (last_iter or {}).get("index"),
            "plan_id": (last_iter or {}).get("plan", {}).get("id"),
            "plan_source": (last_iter or {}).get("plan", {}).get("source"),
            "build_status": (last_iter or {}).get("build_result", {}).get("status"),
            "test_status": (last_iter or {}).get("test_result", {}).get("status"),
            "last_failed_tests": last_failed,
            "last_repair_plan": last_repair,
            "last_optimization_plan": last_opt,
            "last_signals": last_signals,
            "last_quality_score": last_qs,
            "last_loss": last_loss,
            "last_goal_gap": goal_gap,
            "last_findings_count": len(last_findings),
            "blocking_findings": [
                f for f in last_findings if f.get("blocks_delivery") and f.get("evidence")
            ],
        },
        "convergence": last_conv,
        "next_recommended_action": last_conv.get("next_recommended_action"),
        "fake_convergence_findings": last_conv.get("fake_convergence", []),
        "checkpoint_path": str(run_dir(rid, dd) / "checkpoint.json"),
        "memory_packet_count": len(append_memory_packet.__name__ and [] or []),  # placeholder
    }
    # Drop the placeholder
    out.pop("memory_packet_count", None)
    return _emit(out, json_output)


def _lail_kind_summary(signals: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for s in signals:
        k = s.get("kind", "?")
        out[k] = out.get(k, 0) + 1
    return out


# ---------------------------------------------------------------------------
# Deliver command
# ---------------------------------------------------------------------------


def loop_deliver_command(
    run_id: str | None = None,
    json_output: bool = True,
    data_dir: str | None = None,
) -> int:
    """Show the delivery candidate for a run.

    Accepts ``--run-id <id>`` or ``--latest`` (default). The state
    and the candidate are read from disk.
    """
    dd = Path(data_dir) if data_dir else None
    rid = _select_run_id(run_id, dd)
    if rid is None:
        return _emit(
            {"status": "no_run", "message": "Run `loopos loop run <goal>` first."},
            json_output,
        )
    state = read_loop_state(rid, dd)
    candidate = read_delivery_candidate(rid, dd)
    convergence = read_convergence_report(rid, dd)
    iterations = read_iterations(rid, dd)

    if state is None and candidate is None:
        return _emit(
            {"status": "no_run", "run_id": rid},
            json_output,
        )

    # Compute coverage: which required criteria are satisfied.
    items = (state or {}).get("success_criteria", {}).get("items", [])
    required = [c for c in items if c.get("required")]
    satisfied = [c for c in required if c.get("satisfied")]
    unsatisfied = [c for c in required if not c.get("satisfied")]

    fake = (convergence or {}).get("fake_convergence", []) if convergence else []
    open_risks = []
    if candidate is not None:
        open_risks = list(candidate.get("open_risks", []))

    out = {
        "run_id": rid,
        "user_goal": (state or {}).get("goal", {}).get("raw_goal"),
        "delivery_status": (
            "ready" if (candidate and candidate.get("ready"))
            else "blocked_by_fake_convergence" if fake
            else "blocked" if (convergence and convergence.get("status") == "blocked")
            else "budget_exhausted" if (convergence and convergence.get("status") == "iteration_budget_exhausted")
            else "incomplete"
        ),
        "ready": bool(candidate and candidate.get("ready")),
        "why": _why_text(state, candidate, convergence, fake),
        "summary": (candidate or {}).get("summary"),
        "success_criteria_coverage": {
            "required": len(required),
            "satisfied": len(satisfied),
            "unsatisfied": len(unsatisfied),
            "satisfied_ids": [c.get("id") for c in satisfied],
            "unsatisfied_ids": [c.get("id") for c in unsatisfied],
        },
        "remaining_gaps": unsatisfied,
        "fake_convergence_findings": fake,
        "evidence": (candidate or {}).get("evidence", []),
        "open_risks": open_risks,
        "known_limitations": (candidate or {}).get("known_limitations", []),
        "convergence_status": (convergence or {}).get("status"),
        "iterations": len(iterations),
        "recommended_next_loop": _recommended_next_loop(state, candidate, convergence, fake),
        "quality_score": (candidate or {}).get("quality_score"),
    }
    return _emit(out, json_output)


def _why_text(state: Any, candidate: Any, convergence: Any, fake: list[Any]) -> str:
    if candidate and candidate.get("ready"):
        return (
            "All required success criteria satisfied with evidence; "
            "no fake convergence; quality score above threshold."
        )
    if fake:
        return (
            f"Fake convergence detected ({len(fake)} finding(s)); "
            f"delivery blocked until the adversarial evaluator is satisfied."
        )
    if convergence and convergence.get("status") == "iteration_budget_exhausted":
        return "Iteration budget exhausted before the loop converged."
    if convergence and convergence.get("status") == "blocked":
        return "Convergence engine marked this run as blocked."
    if state and state.get("current_status") == "running":
        return "Loop still in progress; delivery not yet evaluated."
    return (
        "Required success criteria are not all satisfied with evidence; "
        "loop should continue."
    )


def _recommended_next_loop(state: Any, candidate: Any, convergence: Any, fake: list[Any]) -> str:
    if fake:
        cats = sorted({f.get("category") for f in fake})
        return (
            f"Run another loop with a new plan that addresses: "
            f"{', '.join(cats)}."
        )
    if convergence and convergence.get("next_recommended_action"):
        return (
            f"Run another loop with action: "
            f"{convergence['next_recommended_action']}."
        )
    return "Run another loop with a fresh plan candidate."


__all__ = [
    "loop_deliver_command",
    "loop_optimize_command",
    "loop_repair_command",
    "loop_review_command",
    "loop_run_command",
    "loop_status_command",
]


# ---------------------------------------------------------------------------
# Other commands (review, repair, optimize)
# ---------------------------------------------------------------------------


def loop_review_command(
    mad_dog: bool = False,
    json_output: bool = True,
    run_id: str | None = None,
    data_dir: str | None = None,
) -> int:
    dd = Path(data_dir) if data_dir else None
    rid = _select_run_id(run_id, dd)
    if rid is None:
        return _emit({"status": "no_run"}, json_output)
    iterations = read_iterations(rid, dd)
    latest = iterations[-1] if iterations else None
    if latest is None:
        return _emit({"status": "no_iterations", "run_id": rid}, json_output)
    out: dict[str, Any] = {
        "run_id": rid,
        "iteration": latest.get("index"),
        "findings": latest.get("review_findings", []),
    }
    if mad_dog:
        reviewer = MadDogReviewer()
        # Recompute mad-dog findings from the latest iteration. We
        # need a LoopState for the goal access, so rebuild a
        # minimal state from the on-disk state.json.
        from loopos.loop_engine.models import (
            BuildResult, PlanCandidate, TestResult, UserGoal, LoopState,
        )
        try:
            ls_state = read_loop_state(rid, dd) or {}
            g = UserGoal(**ls_state.get("goal", {"raw_goal": "?"}))
            ls = LoopState(goal=g)
            plan = PlanCandidate(**latest.get("plan", {}))
            build = BuildResult(**latest.get("build_result", {}))
            tests = TestResult(**latest.get("test_result", {}))
            mds = reviewer.review(ls, plan, build, tests)
            out["mad_dog_findings"] = [m.model_dump(mode="json") for m in mds]
        except Exception as exc:  # noqa: BLE001
            out["mad_dog_error"] = str(exc)
    return _emit(out, json_output)


def loop_repair_command(
    json_output: bool = True,
    run_id: str | None = None,
    data_dir: str | None = None,
) -> int:
    dd = Path(data_dir) if data_dir else None
    rid = _select_run_id(run_id, dd)
    if rid is None:
        return _emit({"status": "no_run"}, json_output)
    iterations = read_iterations(rid, dd)
    latest = iterations[-1] if iterations else None
    if latest is None:
        return _emit({"status": "no_iterations", "run_id": rid}, json_output)
    if latest.get("repair_plan") is None:
        return _emit(
            {"status": "no_repair_plan", "run_id": rid, "iteration": latest.get("index")},
            json_output,
        )
    return _emit(latest["repair_plan"], json_output)


def loop_optimize_command(
    json_output: bool = True,
    run_id: str | None = None,
    data_dir: str | None = None,
) -> int:
    dd = Path(data_dir) if data_dir else None
    rid = _select_run_id(run_id, dd)
    if rid is None:
        return _emit({"status": "no_run"}, json_output)
    state = read_loop_state(rid, dd)
    iterations = read_iterations(rid, dd)
    if state is None or not iterations:
        return _emit({"status": "no_run", "run_id": rid}, json_output)
    # The optimizer works on the latest in-process state, so we
    # rebuild a minimal LoopState-shaped object for the optimizer.
    from loopos.loop_engine.models import (
        SuccessCriteria, UserGoal, SuccessCriterion,
        LoopIteration,
    )
    items = [SuccessCriterion(**c) for c in state["success_criteria"]["items"]]
    sc = SuccessCriteria(items=items, minimum_quality_score=state["success_criteria"].get("minimum_quality_score", 0.75))
    g = UserGoal(**state["goal"])
    state_obj = LoopState(
        goal=g,
        success_criteria=sc,
        max_iterations=state.get("max_iterations", 3),
        trace_id=state.get("trace_id"),
    )
    last = iterations[-1]
    state_obj.iterations = [
        LoopIteration(**{k: v for k, v in last.items() if k in LoopIteration.model_fields})
    ]
    req = FusionOptimizationRequest(
        goal=g,
        success_criteria=sc,
        current_state=state_obj,
        previous_iteration=state_obj.iterations[0] if state_obj.iterations else None,
        mode="consensus",
    )
    opt = FusionOptimizer()
    result = opt.optimize(req)
    return _emit(result.model_dump(mode="json"), json_output)
