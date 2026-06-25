"""Browser computer backend seam."""

from __future__ import annotations

from loopos.computer_control.backends.fake import FakeComputerBackend


class BrowserComputerBackend(FakeComputerBackend):
    """Sandbox browser backend seam, fake until a browser runtime is registered."""

    backend_id = "browser"


__all__ = ["BrowserComputerBackend"]
