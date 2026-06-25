"""Tool permission helpers."""

from __future__ import annotations

from loopos.boundary import ActionBoundaryDecision
from loopos.tools.tool import Tool


def tool_requires_boundary(tool: Tool) -> bool:
    return tool.permission == "action_boundary_required"


def permission_decision(tool: Tool) -> ActionBoundaryDecision:
    return ActionBoundaryDecision(
        allowed=True,
        reason_codes=[f"tool={tool.tool_id}", "action_boundary_required"],
        risk_label="medium",
    )


__all__ = ["permission_decision", "tool_requires_boundary"]
