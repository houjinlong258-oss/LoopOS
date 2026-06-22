"""Typed errors raised by the Agent Loop Interface layer."""

from __future__ import annotations


class AliError(RuntimeError):
    """Base error for the ALI layer."""


class InvalidTransitionError(AliError, ValueError):
    """Raised when an event cannot fire in the current FSM state.

    The error carries the offending state and event so callers can
    surface a clear, audit-friendly reason instead of a bare
    ``ValueError``.
    """


class UnknownEventError(AliError):
    """Raised when an event is not part of the ALI event taxonomy."""


class SessionClosedError(AliError):
    """Raised when a transition is applied to a halted session."""
