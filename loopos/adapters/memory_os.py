"""Project Memory OS adapter contract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class MemoryOSAdapter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter_id: str = "memory_os"
    available: bool = True


__all__ = ["MemoryOSAdapter"]
