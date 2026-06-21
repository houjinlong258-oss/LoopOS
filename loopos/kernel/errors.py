"""Kernel errors for structured error handling."""

from __future__ import annotations


class KernelError(RuntimeError):
    """Base class for kernel errors."""


class InvalidTransitionError(KernelError):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, from_status: str, to_status: str) -> None:
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(f"invalid transition: {from_status} -> {to_status}")


class InvariantViolationError(KernelError):
    """Raised when a kernel invariant is violated and the run must halt."""


class CheckpointError(KernelError):
    """Raised when checkpoint save/load fails."""


class SupervisorHaltError(KernelError):
    """Raised when the supervisor halts a run."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"supervisor halt: {reason}")
