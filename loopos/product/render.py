"""Workbench rendering.

The :func:`render_panels` and :func:`render_panel` functions take a
:class:`PanelLayout` (or a single view) and produce:

* a JSON-friendly dict via :func:`render_json`,
* a human-friendly plain-text block via :func:`render_plain`,
* a short status string via :func:`render_status` for ``--watch``.

The renderer is dependency-free (no Rich, no typer) so it can run
inside the Workbench, the CLI fallback, and unit tests.
"""

from __future__ import annotations

from typing import Any

from loopos.product.panel_layout import DEFAULT_PANEL_ORDER
from loopos.product.views import (
    PanelLayout,
)


def render_panels(panels: PanelLayout) -> str:
    """Render the full panel layout as a plain-text block."""
    blocks: list[str] = []
    for name in DEFAULT_PANEL_ORDER:
        view = _view_by_name(panels, name)
        if view is None:
            continue
        blocks.append(render_panel(view))
    return "\n\n".join(blocks)


def render_panel(view: Any) -> str:
    """Render a single view as a plain-text block."""
    title = getattr(view, "title", "") or view.__class__.__name__
    status = getattr(view, "status", "ok")
    notes = getattr(view, "notes", []) or []
    data = getattr(view, "data", {}) or {}
    panel = getattr(view, "panel", "")
    body = _format_data(data)
    label = f"{panel} {title}" if panel else title
    header = f"┌─ {label} ─"
    if status:
        header += f" [{status}]"
    lines = [header, "│"]
    for line in body.splitlines():
        lines.append(f"│ {line}")
    for note in notes:
        lines.append(f"│ note: {note}")
    lines.append("└" + "─" * max(0, len(header) - 2))
    return "\n".join(lines)


def render_json(panels: PanelLayout) -> dict[str, Any]:
    """Return a JSON-serialisable dict for the layout."""
    return panels.to_dict()


def render_plain(panels: PanelLayout) -> str:
    """Alias for :func:`render_panels` (kept for spec compliance)."""
    return render_panels(panels)


def render_status(panels: PanelLayout) -> str:
    """Short status string for ``--watch`` refreshes."""
    rd = panels.readiness.status
    hf = panels.readiness.data.get("hard_fail_count", 0)
    return f"readiness={rd} hard_fails={hf} panels={len(DEFAULT_PANEL_ORDER)}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _view_by_name(panels: PanelLayout, name: str) -> Any:
    mapping = {
        "goal": panels.goal,
        "agent": panels.agent,
        "policy": panels.policy,
        "aci": panels.aci,
        "ali": panels.ali,
        "trace_replay": panels.trace_replay,
        "fusion": panels.fusion,
        "readiness": panels.readiness,
    }
    return mapping.get(name)


def _format_data(data: dict[str, Any]) -> str:
    if not data:
        return "(no data)"
    out: list[str] = []
    for key, value in data.items():
        if isinstance(value, (list, tuple)):
            if not value:
                out.append(f"{key}: []")
                continue
            out.append(f"{key}:")
            for item in value:
                if isinstance(item, dict):
                    sub = ", ".join(f"{k}={v}" for k, v in item.items())
                    out.append(f"  - {sub}")
                else:
                    out.append(f"  - {item}")
            continue
        if isinstance(value, dict):
            if not value:
                out.append(f"{key}: {{}}")
                continue
            out.append(f"{key}:")
            for k, v in value.items():
                out.append(f"  {k}: {v}")
            continue
        out.append(f"{key}: {value}")
    return "\n".join(out)


__all__ = [
    "render_panels",
    "render_panel",
    "render_json",
    "render_plain",
    "render_status",
]
