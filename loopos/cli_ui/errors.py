from typing import Any
try:
    from rich.panel import Panel
    from rich.console import Group
    from rich.text import Text
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

def render_error_card(title: str, what_happened: str, why: str, fix: str, details: str = "") -> Any:
    if not _HAS_RICH:
        body = f"ERROR {title}\nWhat happened: {what_happened}\nWhy: {why}\nFix: {fix}"
        if details:
            body += f"\nDetails: {details}"
        return body
        
    group = Group(
        Text(what_happened, style="bold red"),
        Text(""),
        Text("Why", style="bold white"),
        Text(f"  {why}", style="white"),
        Text(""),
        Text("Fix", style="bold green"),
        Text(f"  {fix}", style="green"),
        Text("") if details else Text(""),
        Text("Details", style="bold dim") if details else Text(""),
        Text(f"  {details}", style="dim") if details else Text(""),
    )
    return Panel(group, title=f"[bold red]{title}[/bold red]", border_style="red")
