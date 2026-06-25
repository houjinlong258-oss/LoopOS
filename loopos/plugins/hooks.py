"""Plugin hook contract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PluginHook(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hook_id: str
    event: str
    plugin_id: str


__all__ = ["PluginHook"]
