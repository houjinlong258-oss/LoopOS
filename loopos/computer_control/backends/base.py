"""Computer backend protocol."""

from __future__ import annotations

from typing import Protocol

from loopos.computer_control.models import (
    ComputerActionRequest,
    ComputerActionResult,
    ComputerControlSession,
    ComputerObservation,
)


class ComputerBackend(Protocol):
    backend_id: str

    def available(self) -> bool: ...

    def observe(self, session: ComputerControlSession) -> ComputerObservation: ...

    def execute(
        self,
        session: ComputerControlSession,
        action: ComputerActionRequest,
    ) -> ComputerActionResult: ...


__all__ = ["ComputerBackend"]
