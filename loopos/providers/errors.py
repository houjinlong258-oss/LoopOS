"""Typed errors for the :mod:`loopos.providers` package.

All exceptions raised by the Provider Runtime Registry inherit from
:class:`ProviderError`. Consumers should catch :class:`ProviderError`
when they want to handle the whole family; narrower catches are
available for the per-condition cases.
"""

from __future__ import annotations


class ProviderError(Exception):
    """Base class for every provider-registry failure.

    The Provider Runtime Registry is a metadata-only substrate;
    the errors raised here are exclusively about registration,
    lookup, validation, and built-in loading — never about
    network or transport failures, which are out of v0.2 scope.
    """


class ProviderNotFoundError(ProviderError, KeyError):
    """Raised when a provider_id (or alias) is not in the registry.

    The class inherits from both :class:`ProviderError` and
    :class:`KeyError` so that legacy ``except KeyError`` clauses
    in callers continue to work.
    """


class DuplicateProviderError(ProviderError, ValueError):
    """Raised when registering a provider_id that already exists.

    LoopOS governance prefers strict semantics (a duplicate is a
    configuration mistake, not a benign override). This differs
    from Hermes Agent's last-writer-wins convention; see
    ``docs/source-transplant/loopos-transplant-plan.md``.
    """

    def __init__(self, provider_id: str) -> None:
        super().__init__(f"provider_id already registered: {provider_id!r}")
        self.provider_id = provider_id


class ProviderValidationError(ProviderError, ValueError):
    """Raised when a profile fails shape, capability, or base-URL validation.

    The error carries the offending field path and a human-readable
    reason; it never masks the underlying Pydantic ``ValidationError``.
    """
