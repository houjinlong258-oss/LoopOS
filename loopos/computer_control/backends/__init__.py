"""Computer control backend contracts."""

from __future__ import annotations

from loopos.computer_control.backends.base import ComputerBackend
from loopos.computer_control.backends.browser import BrowserComputerBackend
from loopos.computer_control.backends.codex_computer_use import CodexComputerUseAdapter
from loopos.computer_control.backends.cua_mcp import CuaMcpAdapter
from loopos.computer_control.backends.fake import FakeComputerBackend
from loopos.computer_control.backends.local_optional import LocalOptionalComputerBackend

__all__ = [
    "BrowserComputerBackend",
    "CodexComputerUseAdapter",
    "ComputerBackend",
    "CuaMcpAdapter",
    "FakeComputerBackend",
    "LocalOptionalComputerBackend",
]
