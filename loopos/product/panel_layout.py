"""Panel-layout constants.

The Workbench renders a fixed set of panels in a fixed order. The
constants here are the single source of truth for the panel names
and the default ordering.
"""

from __future__ import annotations


PANEL_GOAL = "goal"
PANEL_AGENT = "agent"
PANEL_POLICY = "policy"
PANEL_ACI = "aci"
PANEL_ALI = "ali"
PANEL_TRACE_REPLAY = "trace_replay"
PANEL_FUSION = "fusion"
PANEL_READINESS = "readiness"


DEFAULT_PANEL_ORDER: tuple[str, ...] = (
    PANEL_GOAL,
    PANEL_AGENT,
    PANEL_POLICY,
    PANEL_ACI,
    PANEL_ALI,
    PANEL_TRACE_REPLAY,
    PANEL_FUSION,
    PANEL_READINESS,
)


__all__ = [
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
