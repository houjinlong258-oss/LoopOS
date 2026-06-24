"""Adapter boundary between LAIL and MCP-like tool payloads.

This bridge serializes LAIL messages for tools that may inspect them.
It does not call tools and is not a core dependency of LAIL routing.
"""

from __future__ import annotations

from typing import Any

from loopos.agent_language.message import AgentMessage


class LailMcpBridge:
    """Serialize LAIL messages without executing external tools."""

    core_dependency = False

    def to_tool_payload(self, message: AgentMessage) -> dict[str, Any]:
        return {
            "kind": "lail.adapter_payload",
            "core_dependency": self.core_dependency,
            "message": message.model_dump(mode="json"),
        }

    def supports_execution(self) -> bool:
        return False


__all__ = ["LailMcpBridge"]
