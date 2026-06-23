from __future__ import annotations
from typing import Any

try:
    from rich.theme import Theme
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

THEME_DICT = {
    "cyan": "cyan",               # LoopOS kernel / trace / running
    "green": "green",             # pass / safe / done
    "yellow": "yellow",           # approval / budget warning / caution
    "red": "red",                 # blocked / denied / destructive
    "magenta": "magenta",         # Fusion / Mad Dog / escalation
    "dim_gray": "bright_black",   # metadata / ids / timestamps
    "white": "white",             # default text
}

LOOPOS_THEME: Any = None
if _HAS_RICH:
    LOOPOS_THEME = Theme(THEME_DICT)
