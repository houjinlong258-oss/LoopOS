"""Plugin contract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Plugin(BaseModel):
    """Runtime extension that adds providers, tools, adapters, hooks, or skills."""

    model_config = ConfigDict(extra="forbid")

    plugin_id: str
    name: str
    capabilities: list[str] = Field(default_factory=list)
    optional: bool = True


__all__ = ["Plugin"]
