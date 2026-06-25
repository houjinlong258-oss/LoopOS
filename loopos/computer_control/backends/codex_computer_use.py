"""Optional Codex Computer Use adapter contract."""

from __future__ import annotations

from loopos.computer_control.backends.fake import FakeComputerBackend


class CodexComputerUseAdapter(FakeComputerBackend):
    """Availability-only adapter; it does not execute desktop actions."""

    backend_id = "codex_computer_use"

    def available(self) -> bool:
        return False


__all__ = ["CodexComputerUseAdapter"]
