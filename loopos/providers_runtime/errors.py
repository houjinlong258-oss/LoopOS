"""Provider Runtime error taxonomy."""

from __future__ import annotations


class ProviderRuntimeError(Exception):
    """Base class for all provider runtime errors.

    Subclasses must never include a secret (API key, token) in the
    message. The :func:`loopos.providers_runtime.usage.redact_secrets`
    helper is applied to any externally-sourced string before it is
    surfaced.
    """


class ProviderConfigError(ProviderRuntimeError):
    """Raised when a provider is missing required configuration."""


class ProviderBudgetError(ProviderRuntimeError):
    """Raised when a model call would exceed the configured budget."""


__all__ = [
    "ProviderRuntimeError",
    "ProviderConfigError",
    "ProviderBudgetError",
]
