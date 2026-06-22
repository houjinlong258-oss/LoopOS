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


class ProviderResolutionError(ACIError):
    """Raised when the runner cannot resolve a :class:`ProviderHint`.

    The runner still returns a structured :class:`AgentCommandResult`
    with ``status='failed'`` (or ``status='blocked'`` when the policy
    layer intervenes) and a stable ``reason_code`` such as
    ``provider_not_found`` or ``provider_capability_unavailable``.
    This exception is the strict-mode escape hatch for callers that
    prefer exceptions over results.
    """

    def __init__(self, reason_code: str, message: str = "") -> None:
        super().__init__(message or reason_code)
        self.reason_code = reason_code


class UnsupportedCommandKindError(ACIError):
    """Raised when the runner encounters an unknown ``AgentCommandKind``.

    The runner prefers returning a structured result with
    ``status='unsupported'``; this exception is the strict-mode
    escape hatch.
    """
