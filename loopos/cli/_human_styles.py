"""Shared utilities for ``--human`` mode rendering.

Three responsibilities:

1. **Rich import guard** — single ``HAS_RICH`` / ``require_rich`` helper used
   across CLI renderers (was duplicated in 4+ files).
2. **Mood → color / box / mascot** — the v0.4 ``--human`` panels classify a
   result by *mood* (calm / running / blocked / halted) and derive a color,
   a Rich ``Box`` style, and a Xiao Huanli ASCII face from it. Centralised so
   the run/status/deliver/review/repair/optimize renderers all stay in sync.
3. **Plain-text fallback** — when Rich is not installed we want the same
   flat key:value behaviour the v0.4 closeout shipped, with a small banner
   per status. Implemented in :func:`emit_human_or_fallback`.
"""
from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

try:
    from rich.box import HEAVY, ROUNDED, Box
    from rich.console import Console, Group
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    HAS_RICH = True
except ImportError:  # pragma: no cover - dependency-light envs
    HAS_RICH = False
    Console = None  # type: ignore[assignment,misc]
    Group = None  # type: ignore[assignment,misc]
    Panel = None  # type: ignore[assignment,misc]
    Table = None  # type: ignore[assignment,misc]
    Text = None  # type: ignore[assignment,misc]
    Box = None  # type: ignore[assignment,misc]
    HEAVY = None  # type: ignore[assignment]
    ROUNDED = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Mood → color / box / mascot
# ---------------------------------------------------------------------------

MOOD_COLOR: dict[str, str] = {
    "calm":    "green",
    "running": "cyan",
    "blocked": "red",
    "halted":  "yellow",
}


def mood_box(mood: str) -> Any:
    """Pick a box style that conveys severity.

    ``blocked`` uses ``HEAVY`` so the border itself screams "stop". The
    other moods stay on ``ROUNDED`` for a calmer read.
    """
    if not HAS_RICH:
        return None
    return HEAVY if mood == "blocked" else ROUNDED


def mood_for_obj(obj: dict[str, Any]) -> str:
    """Pick a mood based on the v0.4 result object's status field.

    Order of precedence (highest first):

        1. ``fake_convergence`` / ``fake_convergence_findings`` → ``blocked``.
           Per v0.4 audit doctrine a fake-convergence signal *always*
           blocks the panel — even if ``status`` claims ``ready``. The
           panel must not lie about readiness.
        2. ``current_status`` / ``status`` / ``delivery_status``
        3. default → ``calm``
    """
    # Fake-convergence is a blocker; it wins over any status string.
    if obj.get("fake_convergence") or obj.get("fake_convergence_findings"):
        return "blocked"
    status = (obj.get("current_status") or obj.get("status") or
              obj.get("delivery_status") or "")
    s = str(status).lower()
    if s in {"ready_to_deliver", "ready", "ok", "completed", "pass"}:
        return "calm"
    if s in {"running", "active", "in_progress"}:
        return "running"
    if s in {"blocked", "denied", "halt", "error", "failed"}:
        return "blocked"
    if s in {"halted", "budget_exhausted", "no_repair_plan"}:
        return "halted"
    return "calm"


# Xiao Huanli (the raccoon mascot) — 4-line ASCII, mood-coloured.
# Kept here so all human-mode panels share one canonical art; the legacy
# ``_xiao_huanli`` in loop.py now delegates to :func:`xiao_huanli`.
XIAO_HUANLI_FACES: dict[str, tuple[str, str, str, str]] = {
    # (line1, line2, line3, line4)
    "calm":    ("   /\\_/\\  ", "  (o  o) ", "   (v)   ", "   ||||  "),
    "running": ("   /\\_/\\  ", "  (^  ^) ", "   (v) »»", "   ||||  "),
    "blocked": ("   /\\_/\\  ", "  (>  <) ", "   (X)   ", "   ||||  "),
    "halted":  ("   /\\_/\\  ", "  (T  T) ", "   (o)   ", "   ||||  "),
}


def xiao_huanli(mood: str) -> Any:
    """Return a Rich ``Text`` containing the 4-line mascot for ``mood``.

    Returns ``None`` if Rich is not available so callers can skip the art
    in dependency-light environments.
    """
    if not HAS_RICH:
        return None
    color = MOOD_COLOR.get(mood, "green")
    face = XIAO_HUANLI_FACES.get(mood, XIAO_HUANLI_FACES["calm"])
    return Text("\n".join(face), style=color)


# ---------------------------------------------------------------------------
# Plain-text fallback (no Rich)
# ---------------------------------------------------------------------------


def emit_plain_dict(obj: Any) -> int:
    """Write a flat key:value representation to stdout. Used when Rich
    is unavailable or ``--no-color`` is set."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            sys.stdout.write(f"{k}: {v}\n")
    else:
        sys.stdout.write(str(obj) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Common row builders (markup strings for shared value rendering)
# ---------------------------------------------------------------------------


def kv(key: str, value: Any, *, key_color: str = "bold white",
       value_color: str = "cyan") -> tuple[str, str]:
    """Build a (key, value) tuple of markup strings for :class:`Table.grid`.

    Replaces the dozens of ``f"[bold white]{k}[/bold white]", str(v)`` calls
    scattered across the human-mode renderers. ``value_color`` defaults to
    cyan so unlabeled values light up rather than rendering as plain white.
    """
    return (f"[{key_color}]{key}[/{key_color}]", f"[{value_color}]{value}[/{value_color}]")


def kv_plain(key: str, value: Any, *, key_color: str = "bold white") -> tuple[str, str]:
    """Like :func:`kv` but leaves the value markup-free (e.g. for path-like
    strings where the value is itself a fragment of markup)."""
    return (f"[{key_color}]{key}[/{key_color}]", str(value))


def kvd(key: str, *pairs: tuple[str, Any, str]) -> tuple[str, str]:
    """Key + pre-coloured value-fragments.

    ``pairs`` is ``[(label, value, color), ...]`` rendered as
    ``label=[color]value[/color] label=[color]value[/color]``.

    Example:
        ``kvd("Last quality", ("overall", 0.99, "green"),
              ("test", 1.0, "green"))``
    """
    rendered = "  ".join(
        f"{lbl}=[{col}]{val}[/{col}]" for lbl, val, col in pairs
    )
    return ("[bold white]" + key + "[/bold white]", rendered)


if TYPE_CHECKING:  # pragma: no cover - import-only
    pass