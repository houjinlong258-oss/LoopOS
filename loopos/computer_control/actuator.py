"""Actuator facade for computer-control backends."""

from __future__ import annotations

from loopos.computer_control.backends import ComputerBackend, FakeComputerBackend
from loopos.computer_control.models import (
    ComputerActionRequest,
    ComputerActionResult,
    ComputerControlSession,
)


class ComputerActuator:
    def __init__(self, backend: ComputerBackend | None = None) -> None:
        self.backend = backend or FakeComputerBackend()

    def execute(
        self,
        session: ComputerControlSession,
        action: ComputerActionRequest,
    ) -> ComputerActionResult:
        return self.backend.execute(session, action)


__all__ = ["ComputerActuator"]
