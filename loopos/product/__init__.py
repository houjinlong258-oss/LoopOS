"""LoopOS v0.3 Product Layer — the Workbench.

The product layer is the user-facing surface. It renders the eight
required panels (Goal, Agent, Policy, ACI, ALI, Trace/Replay, Fusion,
Readiness) and dispatches high-level intents into the Agent Bus /
KernelLoopEngine. It **does not** own authority: every side effect
must flow through the existing v0.2 governance stack.
"""

from __future__ import annotations

from loopos.product.workbench import Workbench, WorkbenchContext
from loopos.product.render import (
    render_panels,
    render_panel,
    render_json,
    render_plain,
    render_status,
)
from loopos.product.views import (
    GoalView,
    AgentView,
    PolicyView,
    AciView,
    AliView,
    TraceReplayView,
    FusionView,
    ReadinessView,
    PanelLayout,
)
from loopos.product.commands import build_panels_from_context
from loopos.product.panel_layout import (
    PANEL_GOAL,
    PANEL_AGENT,
    PANEL_POLICY,
    PANEL_ACI,
    PANEL_ALI,
    PANEL_TRACE_REPLAY,
    PANEL_FUSION,
    PANEL_READINESS,
    DEFAULT_PANEL_ORDER,
)

__all__ = [
    "Workbench",
    "WorkbenchContext",
    "render_panels",
    "render_panel",
    "render_json",
    "render_plain",
    "render_status",
    "GoalView",
    "AgentView",
    "PolicyView",
    "AciView",
    "AliView",
    "TraceReplayView",
    "FusionView",
    "ReadinessView",
    "PanelLayout",
    "build_panels_from_context",
    "PANEL_GOAL",
    "PANEL_AGENT",
    "PANEL_POLICY",
    "PANEL_ACI",
    "PANEL_ALI",
    "PANEL_TRACE_REPLAY",
    "PANEL_FUSION",
    "PANEL_READINESS",
    "DEFAULT_PANEL_ORDER",
]
