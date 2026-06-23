from __future__ import annotations
from typing import Any

try:
    from rich.table import Table
    from rich.panel import Panel
    from rich.console import Group
    from rich.text import Text
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

def render_providers_table(rows: list[dict[str, Any]]) -> Table | None:
    if not _HAS_RICH:
        return None
        
    t = Table(box=None, padding=(0, 2), show_header=True)
    t.add_column("Provider", style="cyan")
    t.add_column("Model", style="white")
    t.add_column("Status", style="white")
    t.add_column("Budget", style="yellow")
    
    for r in rows:
        prov = r.get("provider_id", r.get("name", ""))
        model = r.get("default_model", r.get("model", ""))
        status = r.get("status", "")
        budget = r.get("budget_limit", r.get("budget", ""))
        if not budget and "budget_max" in r:
            budget = r["budget_max"]
        if not budget:
            budget = "unlimited"
            
        if status in ("ready", "local"):
            status_markup = f"[green]• {status}[/green]"
        else:
            status_markup = f"[red]• {status}[/red]"
            
        t.add_row(prov, model, status_markup, budget)
    return t

def render_providers_view(rows: list[dict[str, Any]]) -> Any:
    if not _HAS_RICH:
        return ""
    t = render_providers_table(rows)
    assert t is not None
    secrets_text = Text("\nSecrets\n  • stored in environment / keyring\n  • never written to trace\n  • redaction active", style="dim")
    return Panel(Group(t, secrets_text), title="[bold cyan]Providers[/bold cyan]", border_style="cyan")

def render_adapters_table(rows: list[dict[str, Any]]) -> Table | None:
    if not _HAS_RICH:
        return None
        
    t = Table(box=None, padding=(0, 2), show_header=True)
    t.add_column("Adapter", style="cyan")
    t.add_column("Status", style="white")
    t.add_column("Capabilities", style="white")
    
    for r in rows:
        adapter = r.get("adapter_id", "")
        status = r.get("status", "")
        caps = r.get("notes", r.get("capabilities", ""))
        if isinstance(caps, list):
            caps = ", ".join(caps)
            
        if status == "ready":
            status_markup = "[green]ready[/green]"
        elif status == "detected":
            status_markup = "[yellow]detected[/yellow]"
        else:
            status_markup = "[dim]spec-only[/dim]"
            
        t.add_row(adapter, status_markup, caps)
    return t
