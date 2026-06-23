"""Tests for ``loopos.product`` (the Workbench)."""

from __future__ import annotations

import json

from loopos.product import (
    DEFAULT_PANEL_ORDER,
    PANEL_ACI,
    PANEL_AGENT,
    PANEL_ALI,
    PANEL_FUSION,
    PANEL_GOAL,
    PANEL_POLICY,
    PANEL_READINESS,
    PANEL_TRACE_REPLAY,
    PanelLayout,
    Workbench,
    build_panels_from_context,
    render_json,
    render_panel,
    render_plain,
    render_status,
)


def test_workbench_build_context_includes_all_panels() -> None:
    wb = Workbench()
    ctx = wb.build_context(goal={"title": "demo", "intent": "x"}, adapter_id="mock")
    panels = build_panels_from_context(ctx)
    assert isinstance(panels, PanelLayout)
    assert panels.goal.data["title"] == "demo"
    assert panels.agent.data["adapter_id"] == "mock"
    assert panels.policy.data["decision"] in ("allow", "allow_with_constraints")


def test_render_panels_contains_all_panel_labels() -> None:
    wb = Workbench()
    ctx = wb.build_context(goal={"title": "demo"}, adapter_id="mock")
    panels = build_panels_from_context(ctx)
    text = render_plain(panels)
    for name in (
        PANEL_GOAL,
        PANEL_AGENT,
        PANEL_POLICY,
        PANEL_ACI,
        PANEL_ALI,
        PANEL_TRACE_REPLAY,
        PANEL_FUSION,
        PANEL_READINESS,
    ):
        assert name in text, f"panel {name!r} not found in plain output"


def test_render_json_roundtrip() -> None:
    wb = Workbench()
    ctx = wb.build_context(goal={"title": "demo"}, adapter_id="mock")
    panels = build_panels_from_context(ctx)
    payload = render_json(panels)
    serialised = json.dumps(payload, default=str)
    reloaded = json.loads(serialised)
    assert reloaded["goal"]["data"]["title"] == "demo"


def test_render_status_returns_short_string() -> None:
    wb = Workbench()
    ctx = wb.build_context(goal={"title": "demo"})
    panels = build_panels_from_context(ctx)
    status = render_status(panels)
    assert "readiness=" in status
    assert "hard_fails=" in status


def test_default_panel_order_is_eight() -> None:
    assert len(DEFAULT_PANEL_ORDER) == 8
    assert PANEL_GOAL in DEFAULT_PANEL_ORDER
    assert PANEL_READINESS in DEFAULT_PANEL_ORDER


def test_workbench_call_model_dry_run() -> None:
    wb = Workbench()
    out = wb.call_model(
        provider_id="mock", model_id="mock-model", prompt="hi", dry_run=True
    )
    assert out["status"] in ("completed", "dry_run")


def test_workbench_call_model_unknown_provider_blocks() -> None:
    wb = Workbench()
    out = wb.call_model(
        provider_id="does-not-exist", model_id="m", prompt="hi", dry_run=True
    )
    assert out["status"] == "blocked"
    assert "provider_not_found" in out["reason_codes"]


def test_workbench_mad_dog_sets_mode() -> None:
    wb = Workbench()
    ctx = wb.build_context(goal={"title": "demo"}, adapter_id="mock", mode="mad_dog")
    panels = build_panels_from_context(ctx)
    assert panels.fusion.data["mode"] == "mad_dog"


def test_render_panel_renders_a_single_view() -> None:
    wb = Workbench()
    ctx = wb.build_context(goal={"title": "demo"})
    panels = build_panels_from_context(ctx)
    block = render_panel(panels.goal)
    assert "goal_id" in block
    assert "title" in block
