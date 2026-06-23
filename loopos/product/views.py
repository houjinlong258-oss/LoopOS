"""Workbench views (panel data models).

Each view is a small Pydantic model that captures the data the
panel needs to render. Views are read-only: they are built by
:func:`loopos.product.commands.build_panels_from_context` and then
passed to the renderer.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class _BaseView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "0.3"
    title: str = ""
    status: str = "ok"  # "ok" | "warn" | "fail" | "idle" | "running"
    notes: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)


class GoalView(_BaseView):
    panel: str = "goal"


class AgentView(_BaseView):
    panel: str = "agent"


class PolicyView(_BaseView):
    panel: str = "policy"


class AciView(_BaseView):
    panel: str = "aci"


class AliView(_BaseView):
    panel: str = "ali"


class TraceReplayView(_BaseView):
    panel: str = "trace_replay"


class FusionView(_BaseView):
    panel: str = "fusion"


class ReadinessView(_BaseView):
    panel: str = "readiness"


class PanelLayout(BaseModel):
    """Collection of all eight panels, in render order."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "0.3"
    goal: GoalView
    agent: AgentView
    policy: PolicyView
    aci: AciView
    ali: AliView
    trace_replay: TraceReplayView
    fusion: FusionView
    readiness: ReadinessView

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


__all__ = [
    "GoalView",
    "AgentView",
    "PolicyView",
    "AciView",
    "AliView",
    "TraceReplayView",
    "FusionView",
    "ReadinessView",
    "PanelLayout",
]
