"""Tool contract for LoopOS."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Tool(BaseModel):
    """A typed callable action that can change project state."""

    model_config = ConfigDict(extra="forbid")

    tool_id: str
    name: str
    description: str
    capabilities: list[str] = Field(default_factory=list)
    permission: str = "action_boundary_required"
    schema_tokens_estimate: int = 0


__all__ = ["Tool"]
