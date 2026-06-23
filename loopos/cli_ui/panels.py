from __future__ import annotations
from typing import Any

try:
    from rich.panel import Panel
    from rich.table import Table
    from rich.columns import Columns
    from rich.console import Group
    from rich.text import Text
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False


def render_view_rich(view: Any) -> Any:
    if not _HAS_RICH:
        return str(view)
        
    title = getattr(view, "title", "") or view.__class__.__name__
    status = getattr(view, "status", "ok")
    notes = getattr(view, "notes", []) or []
    data = getattr(view, "data", {}) or {}
    panel_name = getattr(view, "panel", "")
    
    border_style = "dim"
    status_text = ""
    if status:
        if status in ("allow", "safe", "PASS", "ready", "deterministic", "success", "COMPLETED", "active", "enabled"):
            status_style = "green"
            border_style = "green"
        elif status in ("approval_required", "waiting_approval", "warning", "caution"):
            status_style = "yellow"
            border_style = "yellow"
        elif status in ("blocked", "denied", "halt", "error", "missing"):
            status_style = "red"
            border_style = "red"
        else:
            status_style = "cyan"
            border_style = "cyan"
        status_text = f" [{status_style}]{status}[/{status_style}]"
        
    label = f"{panel_name} {title}" if panel_name else title
    title_markup = f"[bold white]{label}[/bold white]{status_text}"
    
    body = Table.grid(padding=(0, 2))
    body.add_column(style="bold cyan", width=15)
    body.add_column(style="white")
    
    for key, value in data.items():
        if key == "rows":
            continue
        k_disp = key.replace("_", " ").title()
        body.add_row(k_disp, str(value))
        
    if notes:
        body.add_row("", "")
        for note in notes:
            body.add_row("[dim]note[/dim]", f"[dim]{note}[/dim]")
            
    return Panel(body, title=title_markup, border_style=border_style)

def render_panels_rich(panels: Any) -> Group:
    p_goal = render_view_rich(panels.goal)
    p_agent = render_view_rich(panels.agent)
    p_policy = render_view_rich(panels.policy)
    
    aci_data = getattr(panels.aci, "data", {}) or {}
    aci_rows = aci_data.get("rows", [])
    if aci_rows:
        t = Table(box=None, padding=(0, 1), show_header=True)
        t.add_column("ID", style="dim")
        t.add_column("Kind", style="cyan")
        t.add_column("Risk", style="white")
        t.add_column("Policy", style="green")
        t.add_column("Status", style="green")
        for row in aci_rows:
            risk = row.get("risk_hint", "low")
            risk_color = "red" if risk == "high" else ("yellow" if risk == "medium" else "green")
            risk_markup = f"[{risk_color}]{risk}[/{risk_color}]"
            
            pol = row.get("policy_decision", "")
            pol_color = "green" if pol in ("allow", "allowed") else "yellow"
            pol_markup = f"[{pol_color}]{pol}[/{pol_color}]"
            
            status = row.get("status", "")
            status_color = "green" if status == "PASS" else ("yellow" if status == "PENDING" else "red")
            status_markup = f"[{status_color}]{status}[/{status_color}]"
            
            t.add_row(row.get("command_id", ""), row.get("kind", ""), risk_markup, pol_markup, status_markup)
        p_aci = Panel(t, title=f"[bold white]aci ACI Commands[/bold white] [{panels.aci.status}]", border_style="dim")
    else:
        p_aci = render_view_rich(panels.aci)
        
    p_ali = render_view_rich(panels.ali)
    p_trace = render_view_rich(panels.trace_replay)
    p_fusion = render_view_rich(panels.fusion)
    p_readiness = render_view_rich(panels.readiness)
    
    grid = Table.grid(expand=True, padding=(1, 1))
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)
    
    grid.add_row(p_goal, p_agent, p_policy)
    grid.add_row(p_aci, p_ali, p_trace)
    grid.add_row(p_fusion, p_readiness, Panel(Text("Recent Events:\nNone", style="dim"), title="Events", border_style="dim"))
    
    return Group(grid)

def render_home_dashboard(project_data: dict[str, Any], runtime_data: dict[str, Any], providers_data: list[dict[str, Any]]) -> Any:
    grid_header = Table.grid(expand=True)
    grid_header.add_column(width=12)
    grid_header.add_column()
    
    cat_lines = [
        "   /\\_/\\  ",
        "  ( o.o ) ",
        "   /∞\\    ",
        "  /___\\ ))="
    ]
    cat_text = Text("\n".join(cat_lines), style="cyan")
    
    title_text = Text.assemble(
        ("LoopOS v0.3\n", "bold cyan"),
        ("The command center for governed agents\n", "white"),
        ("Think freely. Act governed.", "dim")
    )
    grid_header.add_row(cat_text, title_text)
    header = Panel(grid_header, border_style="cyan")
    
    proj_table = Table.grid(padding=(0, 2))
    proj_table.add_column(style="bold white", width=12)
    proj_table.add_column(style="cyan")
    for k, v in project_data.items():
        proj_table.add_row(k, str(v))
    proj_panel = Panel(proj_table, title="[bold white]Project[/bold white]", border_style="dim")
    
    rt_table = Table.grid(padding=(0, 2))
    rt_table.add_column(style="bold white", width=12)
    rt_table.add_column(style="green")
    for k, v in runtime_data.items():
        color = "green" if v in ("ready", "active", "enabled", "on") else "yellow"
        rt_table.add_row(k, f"[{color}]{v}[/{color}]")
    rt_panel = Panel(rt_table, title="[bold white]Runtime[/bold white]", border_style="dim")
    
    prov_table = Table(box=None, padding=(0, 1), show_header=False)
    prov_table.add_column(style="bold white")
    prov_table.add_column()
    for prov in providers_data:
        status = prov.get("status", "")
        color = "green" if status in ("ready", "local") else "red"
        prov_table.add_row(prov.get("name", prov.get("provider_id", "")), f"[{color}]{status}[/{color}]")
    prov_panel = Panel(prov_table, title="[bold white]Providers[/bold white]", border_style="dim")
    
    cmd_table = Table.grid(padding=(0, 2))
    cmd_table.add_column(style="cyan", width=35)
    cmd_table.add_column(style="white")
    cmd_table.add_row("loopos run goal.md", "run a governed task")
    cmd_table.add_row("loopos attach hermes", "attach an agent kernel")
    cmd_table.add_row("loopos mad-dog bug.md", "escalate hard problems")
    cmd_table.add_row("loopos replay <run-id>", "replay a trace")
    cmd_table.add_row("loopos readiness check", "verify the runtime")
    cmd_panel = Panel(cmd_table, title="[bold white]Commands[/bold white]", border_style="dim")
    
    top_cols = Columns([proj_panel, rt_panel, prov_panel], expand=True)
    return Group(header, top_cols, cmd_panel)

def render_approval_required(
    command: str, target: str, risk: str, policy: str, reason: str,
    diff_summary: str, safety_checks: list[dict[str, Any]]
) -> Panel:
    cat_lines = [
        "   /\\_/\\  ",
        "  ( o.o ) ",
        "   /∞\\    ",
        "  /___\\ ))="
    ]
    cat_text = Text("\n".join(cat_lines), style="yellow")
    
    details = Table.grid(padding=(0, 2))
    details.add_column(style="bold white", width=12)
    details.add_column(style="yellow")
    details.add_row("Command", command)
    details.add_row("Target", target)
    details.add_row("Risk", risk)
    details.add_row("Policy", policy)
    details.add_row("Reason", reason)
    
    top_grid = Table.grid(expand=True)
    top_grid.add_column(width=12)
    top_grid.add_column()
    top_grid.add_row(cat_text, details)
    
    diff_panel = Panel(Text(diff_summary, style="white"), title="Diff Summary", border_style="dim")
    
    checks_text = Text()
    for check in safety_checks:
        status_char = "✓" if check.get("passed", True) else "✗"
        status_color = "green" if check.get("passed", True) else "red"
        checks_text.append(f" {status_char} ", style=f"bold {status_color}")
        checks_text.append(f"{check.get('name', '')}\n", style="white")
        
    checks_panel = Panel(checks_text, title="Safety Checks", border_style="dim")
    
    bottom_grid = Table.grid(expand=True, padding=(0, 2))
    bottom_grid.add_column(ratio=1)
    bottom_grid.add_column(ratio=1)
    bottom_grid.add_row(diff_panel, checks_panel)
    
    choices = Text("\nChoices:\n  [a] approve once   [v] view full diff   [r] request smaller patch   [d] deny", style="bold yellow")
    
    group = Group(top_grid, Text(""), bottom_grid, Text(""), choices)
    return Panel(group, title="[bold yellow]Approval Required[/bold yellow]", border_style="yellow")

def render_blocked_by_policy(
    command: str, input_str: str, policy: str, reason: str, trace_id: str
) -> Panel:
    cat_lines = [
        "   /\\_/\\  ",
        "  ( o.o ) ",
        "   /∞\\    ",
        "  /___\\ ))="
    ]
    cat_text = Text("\n".join(cat_lines), style="red")
    
    details = Table.grid(padding=(0, 2))
    details.add_column(style="bold white", width=12)
    details.add_column(style="red")
    details.add_row("Command", command)
    details.add_row("Input", input_str)
    details.add_row("Policy", policy)
    details.add_row("Decision", "blocked")
    details.add_row("Reason", reason)
    details.add_row("Trace ID", trace_id)
    
    top_grid = Table.grid(expand=True)
    top_grid.add_column(width=12)
    top_grid.add_column()
    top_grid.add_row(cat_text, details)
    
    what_to_do = Text(
        "\nWhat you can do:\n"
        "  1. Ask agent to inspect files instead\n"
        "  2. Narrow the target path\n"
        "  3. Run in dry-run mode\n"
        "  4. Change policy only after human review",
        style="white"
    )
    
    group = Group(
        Text("Command denied before execution. No side effects occurred.", style="bold red"),
        Text(""),
        top_grid,
        what_to_do
    )
    return Panel(group, title="[bold red]Blocked by Policy OS[/bold red]", border_style="red")

def render_run_complete(
    status: str, state: str, duration: str, budget_used: str, budget_max: str,
    trace_id: str, what_changed: list[str], proofs: list[str]
) -> Panel:
    details = Table.grid(padding=(0, 2))
    details.add_column(style="bold white", width=12)
    details.add_column(style="green")
    details.add_row("Status", status)
    details.add_row("State", state)
    details.add_row("Duration", duration)
    details.add_row("Budget", f"{budget_used} / {budget_max}")
    details.add_row("Trace ID", trace_id)
    
    changed_text = Text()
    for item in what_changed:
        changed_text.append(f"  modified  {item}\n", style="green")
    changed_panel = Panel(changed_text or Text("  no files modified", style="dim"), title="What Changed", border_style="dim")
    
    proofs_text = Text()
    for proof in proofs:
        proofs_text.append(f"  ✓ {proof}\n", style="green")
    proofs_panel = Panel(proofs_text, title="Proof", border_style="dim")
    
    bottom_grid = Table.grid(expand=True, padding=(0, 2))
    bottom_grid.add_column(ratio=1)
    bottom_grid.add_column(ratio=1)
    bottom_grid.add_row(changed_panel, proofs_panel)
    
    next_steps = Text(
        f"\nNext Steps:\n"
        f"  loopos trace show {trace_id}\n"
        f"  loopos replay {trace_id}\n"
        f"  loopos report {trace_id}",
        style="bold green"
    )
    
    group = Group(details, Text(""), bottom_grid, next_steps)
    return Panel(group, title="[bold green]Run Complete[/bold green]", border_style="green")
