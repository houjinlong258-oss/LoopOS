"""Local optional backend seam."""

from __future__ import annotations

from loopos.computer_control.backends.fake import FakeComputerBackend


class LocalOptionalComputerBackend(FakeComputerBackend):
    """Local desktop backend is opt-in and unavailable without dependencies."""

    backend_id = "local_optional"

    def available(self) -> bool:
        return False


__all__ = ["LocalOptionalComputerBackend"]
