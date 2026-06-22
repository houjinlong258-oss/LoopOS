"""Provider-hint resolution helper for the ACI runner.

This module owns the single ``_resolve_provider_hint`` helper that
maps a :class:`ProviderHint` to a :class:`ResolvedProvider` (or a
structured failure triple). The runner composes this helper for
both the early provider-resolution step in :meth:`CommandRunner.run`
and the strict :meth:`CommandRunner.resolve_provider` escape hatch.

The helper is intentionally pure and metadata-only:

* It never makes a live provider API call.
* It never raises on resolution failure; it returns a
  ``(None, reason_code, message)`` triple. The runner turns the
  tuple into a structured :class:`AgentCommandResult`.
* The triple is also stable enough to be re-raised as
  :class:`ProviderResolutionError` for callers that opt into a
  strict exception-style flow.

Resolution order (matches the Phase 2 contract):

1. ``provider_id`` set -> exact lookup.
2. ``local_only=True`` -> only local profiles considered.
3. ``required_capabilities`` non-empty -> capability lookup,
   deterministically ordered by ``provider_id``.
4. ``preferred_kind`` -> kind-only filter.
5. No criterion -> structured failure
   (``provider_hint has no provider_id, no required_capabilities,
   no local_only, and no preferred_kind``).
"""

from __future__ import annotations

from typing import Any

from loopos.aci.models import (
    REASON_PROVIDER_CAPABILITY_UNAVAILABLE,
    REASON_PROVIDER_LOCAL_ONLY_REQUIRED,
    REASON_PROVIDER_NOT_FOUND,
    ProviderHint,
    ProviderResolutionSource,
    ResolvedProvider,
)


def _to_resolved(profile: Any, source: ProviderResolutionSource) -> ResolvedProvider:
    """Convert a registry profile into a :class:`ResolvedProvider`.

    Exposed at module scope (leading underscore is conventional for
    "private to the package") so the runner can compose it without
    re-implementing the conversion.
    """

    caps = list(profile.capability_hints.capabilities)
    return ResolvedProvider(
        provider_id=profile.provider_id,
        display_name=profile.name,
        kind=str(profile.kind),
        capabilities=caps,
        source=source,
        reason_code="",
    )


def resolve_provider_hint(
    hint: ProviderHint,
    registry: "Any | None",  # ProviderRegistry or None
) -> tuple[ResolvedProvider | None, str | None, str | None]:
    """Resolve a :class:`ProviderHint` against a registry.

    Returns a ``(resolved, reason_code, message)`` triple.

    * ``resolved`` is non-None only on success.
    * ``reason_code`` is one of the stable provider reason codes on
      failure (e.g. ``provider_not_found``).
    * ``message`` is a human-readable diagnostic. ``reason_code`` is
      what callers should assert against.

    The function never raises on resolution failure; it returns a
    ``(None, reason_code, message)`` tuple. The runner turns the
    tuple into a structured :class:`AgentCommandResult`. Strict
    callers can re-raise via :class:`ProviderResolutionError`.

    Public name ``resolve_provider_hint`` is the canonical entry
    point; the runner aliases the legacy underscore-prefixed name
    for backward compatibility within the package.
    """

    if registry is None:
        return None, REASON_PROVIDER_NOT_FOUND, (
            "provider_hint supplied but no provider registry was wired into the runner"
        )

    try:
        # 1. Exact match.
        if hint.provider_id:
            exact = registry.try_get(hint.provider_id)
            if exact is None:
                return (
                    None,
                    REASON_PROVIDER_NOT_FOUND,
                    f"provider_id {hint.provider_id!r} not in registry",
                )
            return _to_resolved(exact, "exact"), None, None

        # 2. Local-only filter.
        if hint.local_only is True:
            local_matches = list(registry.find_local())
            if not local_matches:
                return (
                    None,
                    REASON_PROVIDER_LOCAL_ONLY_REQUIRED,
                    "no local-only provider available",
                )
            chosen = local_matches[0]
            return _to_resolved(chosen, "local"), None, None

        # 3. Capability filter (and optional kind narrowing).
        if hint.required_capabilities:
            candidates = []
            for cap in hint.required_capabilities:
                candidates.extend(registry.find_by_capability(cap))
            # Deduplicate by provider_id while preserving order.
            seen: set[str] = set()
            deduped: list[Any] = []
            for p in candidates:
                if p.provider_id in seen:
                    continue
                seen.add(p.provider_id)
                deduped.append(p)
            if hint.preferred_kind is not None:
                deduped = [p for p in deduped if str(p.kind) == hint.preferred_kind]
            if not deduped:
                return (
                    None,
                    REASON_PROVIDER_CAPABILITY_UNAVAILABLE,
                    f"no provider matches required_capabilities={hint.required_capabilities!r}",
                )
            # Deterministic: pick the alphabetically smallest provider_id.
            # ``allow_fallback`` does not block capability-based resolution:
            # there is no "original" provider to fall back from; we are
            # already choosing among equivalent candidates.
            deduped.sort(key=lambda p: p.provider_id)
            return _to_resolved(deduped[0], "capability"), None, None

        # 4. Kind-only filter.
        if hint.preferred_kind is not None:
            kind_matches = [
                p for p in registry.list()
                if str(p.kind) == hint.preferred_kind
            ]
            if not kind_matches:
                return (
                    None,
                    REASON_PROVIDER_NOT_FOUND,
                    f"no provider with preferred_kind={hint.preferred_kind!r}",
                )
            return _to_resolved(kind_matches[0], "kind"), None, None

        # 5. No criterion: provider_id is required when nothing else is set.
        return (
            None,
            REASON_PROVIDER_NOT_FOUND,
            "provider_hint has no provider_id, no required_capabilities, "
            "no local_only, and no preferred_kind; nothing to resolve",
        )
    except Exception as exc:  # noqa: BLE001 - defensive boundary
        return None, REASON_PROVIDER_NOT_FOUND, f"provider resolution raised: {exc}"


# ---------------------------------------------------------------------------
# Backward-compat alias.
#
# The original runner used the underscore-prefixed private name
# ``_resolve_provider_hint``. Re-export it under the same name so
# other internal helpers (and any tests that reach for the private
# name) keep working unchanged.
# ---------------------------------------------------------------------------

_resolve_provider_hint = resolve_provider_hint


__all__ = [
    "resolve_provider_hint",
]