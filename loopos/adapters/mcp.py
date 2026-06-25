"""Optional MCP adapter contract for LAIL signals."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class McpAdapter(BaseModel):
    """Metadata-only MCP adapter; unavailable until a server is registered."""

    model_config = ConfigDict(extra="forbid")

    adapter_id: str = "mcp"
    available: bool = False

    def translate_lail(self, signal: dict[str, object]) -> dict[str, object]:
        return {"adapter_id": self.adapter_id, "available": self.available, "signal": signal}


__all__ = ["McpAdapter"]
