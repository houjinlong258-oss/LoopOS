"""Observer facade for computer-control backends."""

from __future__ import annotations

from loopos.computer_control.backends import ComputerBackend, FakeComputerBackend
from loopos.computer_control.models import ComputerControlSession, ComputerObservation


class ComputerObserver:
    def __init__(self, backend: ComputerBackend | None = None) -> None:
        self.backend = backend or FakeComputerBackend()

    def observe(self, session: ComputerControlSession) -> ComputerObservation:
        return self.backend.observe(session)


__all__ = ["ComputerObserver"]
