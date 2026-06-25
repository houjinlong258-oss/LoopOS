"""Node capability declarations."""

from __future__ import annotations

from typing import Literal


Capability = Literal[
    "shell.exec",
    "file.patch",
    "test.run",
    "browser.control",
    "computer.observe",
    "computer.click",
    "computer.type",
    "screen.capture",
    "clipboard.read_redacted",
    "app.open",
    "ui.verify",
    "provider.call",
    "memory.retrieve",
]

DEFAULT_LOCAL_CAPABILITIES: tuple[Capability, ...] = (
    "shell.exec",
    "file.patch",
    "test.run",
    "computer.observe",
    "screen.capture",
    "clipboard.read_redacted",
    "provider.call",
    "memory.retrieve",
)


__all__ = ["Capability", "DEFAULT_LOCAL_CAPABILITIES"]
