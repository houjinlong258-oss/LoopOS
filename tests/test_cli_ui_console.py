from __future__ import annotations
import json
from typing import Any
from unittest.mock import patch

from loopos.cli_ui import make_console, is_ci, emit_json, get_mascot
from loopos.cli_ui.panels import render_view_rich
from loopos.cli_ui.tables import render_providers_table, render_adapters_table
from loopos.product import Workbench, build_panels_from_context

def test_cli_ui_import_behavior() -> None:
    assert isinstance(is_ci(), bool)
    with patch("loopos.cli_ui.console._HAS_RICH", False):
        assert make_console() is None

def test_json_bypasses_rich(capsys: Any) -> None:
    payload = {"status": "ok", "data": [1, 2, 3]}
    emit_json(payload)
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed == payload
    assert "\x1b[" not in captured.out

def test_no_color_disables_styling() -> None:
    con = make_console(no_color=True)
    if con is not None:
        assert con.color_system is None

def test_ci_non_tty_no_live() -> None:
    with patch.dict("os.environ", {"CI": "true"}):
        assert is_ci() is True
        con = make_console()
        if con is not None:
            assert con.color_system is None

def test_mascot_only_on_human_output() -> None:
    mascot = get_mascot(compact=False)
    assert "LoopOS" in mascot
    assert "o.o" in mascot
    assert get_mascot(compact=True) == "( o.o )∞"

def test_workbench_output_includes_panel_names() -> None:
    wb = Workbench()
    ctx = wb.build_context(goal={"title": "demo"}, dry_run=True)
    panels = build_panels_from_context(ctx)
    
    v_goal = render_view_rich(panels.goal)
    assert "goal" in str(v_goal.title).lower()
    
    v_agent = render_view_rich(panels.agent)
    assert "agent" in str(v_agent.title).lower()
    
    v_policy = render_view_rich(panels.policy)
    assert "policy" in str(v_policy.title).lower()

def test_tables_fallback_cleanly_without_rich() -> None:
    with patch("loopos.cli_ui.tables._HAS_RICH", False):
        assert render_providers_table([]) is None
        assert render_adapters_table([]) is None
