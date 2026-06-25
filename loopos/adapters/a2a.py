"""A2A adapter placeholder."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class A2AAdapter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter_id: str = "a2a"
    available: bool = False


__all__ = ["A2AAdapter"]
