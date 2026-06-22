"""Typed errors raised by the Agent Command Interface layer.

ACI never lets exceptions escape silently. Callers can use these
typed errors to surface clear, auditable failure reasons to the
agent or to the runtime loop.
"""

from __future__ import annotations


class ACIError(RuntimeError):
    """Base error for the ACI layer."""


class CommandValidationError(ACIError, ValueError):
    """Raised when an :class:`AgentCommand` fails validation.

    Validation includes JSON parsing, missing required fields, and
    schema-level semantic checks. ACI does not execute anything when
    validation fails.
    """


class PolicyDeniedError(ACIError):
    """Raised when Policy OS denies a command.

    The runner still returns a structured :class:`AgentCommandResult`
    for the denial; this exception is reserved for callers that opt
    into a strict exception-style flow.
    """


class CommandBlockedError(ACIError):
    """Raised when the command cannot be routed through the syscall path.

    Examples include unknown syscall names, missing adapters, or a
    non-allowlisted path that the boundary check refuses.
    """
