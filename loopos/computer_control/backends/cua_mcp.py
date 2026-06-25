"""Optional CUA MCP adapter contract."""

from __future__ import annotations

from loopos.computer_control.backends.fake import FakeComputerBackend


class CuaMcpAdapter(FakeComputerBackend):
    """Optional registered-server adapter; unavailable by default."""

    backend_id = "cua_mcp"

    def available(self) -> bool:
        return False


__all__ = ["CuaMcpAdapter"]
