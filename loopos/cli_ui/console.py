from __future__ import annotations
import os

try:
    from rich.console import Console
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

_console: Console | None = None

def is_ci() -> bool:
    return os.getenv("CI", "").lower() in {"1", "true", "yes", "on"}

def make_console(no_color: bool = False, quiet: bool = False, force_terminal: bool | None = None) -> Console | None:
    global _console
    if not _HAS_RICH:
        return None
        
    if _console is not None and not no_color and not quiet and force_terminal is None:
        return _console
    
    from typing import Any
    color_system: Any = None
    if not no_color and not is_ci():
        color_system = "auto"
        
    con = Console(
        color_system=color_system,
        force_terminal=force_terminal if force_terminal is not None else (None if is_ci() else True),
        width=100 if is_ci() else None
    )
    if not no_color and not quiet and force_terminal is None:
        _console = con
    return con

def get_console() -> Console | None:
    global _console
    if _console is None:
        _console = make_console()
    return _console
