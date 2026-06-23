"""LoopOS v0.3 Rich CLI / TUI product layer."""

from __future__ import annotations

from loopos.cli_ui.console import make_console, is_ci, get_console
from loopos.cli_ui.theme import LOOPOS_THEME
from loopos.cli_ui.mascot import get_mascot, MASCOT_LARGE, MASCOT_COMPACT, PROMPT_SYMBOL
from loopos.cli_ui.json import emit_json
from loopos.cli_ui.panels import (
    render_view_rich,
    render_panels_rich,
    render_home_dashboard,
    render_approval_required,
    render_blocked_by_policy,
    render_run_complete,
)
from loopos.cli_ui.tables import render_providers_table, render_providers_view, render_adapters_table
from loopos.cli_ui.progress import render_pipeline
from loopos.cli_ui.errors import render_error_card
from loopos.cli_ui.diff import render_diff

__all__ = [
    "make_console",
    "is_ci",
    "get_console",
    "LOOPOS_THEME",
    "get_mascot",
    "MASCOT_LARGE",
    "MASCOT_COMPACT",
    "PROMPT_SYMBOL",
    "emit_json",
    "render_view_rich",
    "render_panels_rich",
    "render_home_dashboard",
    "render_approval_required",
    "render_blocked_by_policy",
    "render_run_complete",
    "render_providers_table",
    "render_providers_view",
    "render_adapters_table",
    "render_pipeline",
    "render_error_card",
    "render_diff",
]
