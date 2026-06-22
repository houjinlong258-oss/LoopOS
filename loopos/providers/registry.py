"""In-memory Provider Runtime Registry for LoopOS.

The :class:`ProviderRegistry` is a metadata-only substrate. It does
NOT make network calls, does NOT instantiate HTTP clients, and does
NOT probe providers for live model lists. Its sole responsibility is
to hold a deterministic, queryable collection of
:class:`loopos.providers.models.ModelProviderProfile` instances.

Design provenance
-----------------

The **API shape** is borrowed from Hermes Agent's
``providers/__init__.py`` (MIT, © 2025 Nous Research). LoopOS
re-implements it with stricter semantics:

* ``register(profile)`` **rejects duplicates** (raises
  :class:`DuplicateProviderError`). Hermes uses last-writer-wins;
  LoopOS governance prefers explicit failure on configuration
  mistakes.

* ``get(provider_id)`` raises :class:`ProviderNotFoundError` on a
  miss rather than returning ``None``. Strict.

* ``find_by_capability(capability)`` returns **all** matches in
  insertion order, not just the best one. Hermes's ``route()``
  returns the single best; LoopOS defers selection to v0.3+
  ``loopos.providers.selection``.

* ``load_builtin_profiles()`` is explicit rather than implicit. No
  filesystem scanning on first access; no lazy discovery; no user
  plugin directories in v0.2. The v0.3+ design will revisit.

* ``validate_profile(profile)`` is exposed publicly so tests and
  external callers can assert shape without instantiating the
  registry.

Coexistence with :mod:`loopos.model_kernel`
------------------------------------------

``loopos.model_kernel.ProviderRegistry`` owns the scheduler-aware
runtime registry; ``loopos.providers.ProviderRegistry`` is the
metadata-only substrate above. The two never import from each
other. See ``loopos/providers/models.py`` docstring for the full
boundary statement.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from loopos.providers.errors import (
    DuplicateProviderError,
    ProviderNotFoundError,
    ProviderValidationError,
)
from loopos.providers.models import (
    ModelCapability,
    ModelProviderProfile,
    ProviderKind,
)

logger = logging.getLogger(__name__)


# Map from provider_id -> ProviderKind inferred when loading from YAML.
# The loader treats any provider_id not listed here as
# ``openai_compatible``, which is the right default for the bulk of
# Hermes-style OpenAI-compat providers.
_KIND_BY_PROVIDER_ID: dict[str, ProviderKind] = {
    "anthropic": "anthropic_messages",
    "gemini": "gemini",
    "bedrock": "bedrock",
    "azure-foundry": "azure_ai_foundry",
    "custom": "custom_openai_compatible",
    "ollama-cloud": "local_openai_compatible",
    "huggingface": "local_openai_compatible",
}


class ProviderRegistry:
    """In-memory, metadata-only registry of :class:`ModelProviderProfile`.

    The registry is deterministic: ``list()`` returns profiles in
    insertion order; ``find_by_capability()`` preserves that order.
    There is no lazy loading, no I/O after construction, and no
    background refresh.
    """

    def __init__(self) -> None:
        self._profiles: dict[str, ModelProviderProfile] = {}
        self._aliases: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, profile: ModelProviderProfile) -> None:
        """Register ``profile`` under its ``provider_id``.

        Raises
        ------
        ProviderValidationError
            If ``profile`` is not a :class:`ModelProviderProfile`.
        DuplicateProviderError
            If the ``provider_id`` is already registered.

        Notes
        -----
        Aliases are refreshed: any prior alias mapping for this
        provider_id (e.g. set by an earlier profile sharing the
        same primary key) is cleared and the new aliases replace
        it. LoopOS rejects duplicate primary keys; reusing an
        alias is silently allowed only when the alias points to a
        single registered profile.
        """
        if not isinstance(profile, ModelProviderProfile):
            raise ProviderValidationError(
                f"profile must be a ModelProviderProfile instance, got {type(profile).__name__}"
            )
        # Validate via Pydantic on construction — redundant but explicit.
        ModelProviderProfile.model_validate(profile.model_dump())

        pid = profile.provider_id
        if pid in self._profiles:
            raise DuplicateProviderError(pid)

        # Drop any stale aliases pointing at this provider_id (would only
        # happen if the registry is reused after clear() with re-population).
        for alias in list(self._aliases):
            if self._aliases[alias] == pid:
                self._aliases.pop(alias, None)

        self._profiles[pid] = profile
        for alias in profile.aliases:
            a = alias.strip()
            if not a:
                continue
            if a == pid:
                continue
            if a in self._aliases and self._aliases[a] != pid:
                raise DuplicateProviderError(a)
            self._aliases[a] = pid

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, provider_id: str) -> ModelProviderProfile:
        """Return the profile for ``provider_id`` (or alias).

        Raises :class:`ProviderNotFoundError` if not found. The
        alias lookup is case-sensitive on the alias string (callers
        should pass the canonical alias registered by the profile).
        """
        canonical = self._aliases.get(provider_id, provider_id)
        profile = self._profiles.get(canonical)
        if profile is None:
            raise ProviderNotFoundError(provider_id)
        return profile

    def try_get(self, provider_id: str) -> ModelProviderProfile | None:
        """Return the profile or ``None`` if missing.

        Useful for callers that want to ask politely without
        try/except. Identical semantics to :meth:`get` apart from
        the return-on-miss.
        """
        try:
            return self.get(provider_id)
        except ProviderNotFoundError:
            return None

    def contains(self, provider_id: str) -> bool:
        """Return True if a profile is registered under ``provider_id`` or any alias."""
        return self.try_get(provider_id) is not None

    def list(self) -> tuple[ModelProviderProfile, ...]:
        """Return all profiles in stable insertion order."""
        return tuple(self._profiles.values())

    def ids(self) -> tuple[str, ...]:
        """Return all registered ``provider_id`` values in insertion order."""
        return tuple(self._profiles.keys())

    def aliases(self) -> dict[str, str]:
        """Return a snapshot copy of the alias-to-canonical map."""
        return dict(self._aliases)

    def find_by_capability(
        self, capability: ModelCapability
    ) -> tuple[ModelProviderProfile, ...]:
        """Return all profiles that declare ``capability``.

        Insertion order is preserved. An empty capability token
        raises :class:`ProviderValidationError`.
        """
        if not isinstance(capability, str) or not capability.strip():
            raise ProviderValidationError("capability must be a non-empty string")
        return tuple(
            profile
            for profile in self._profiles.values()
            if profile.has_capability(capability)  # type: ignore[arg-type]
        )

    def find_by_kind(self, kind: ProviderKind) -> tuple[ModelProviderProfile, ...]:
        """Return all profiles whose ``kind`` matches."""
        return tuple(profile for profile in self._profiles.values() if profile.kind == kind)

    def find_local(self) -> tuple[ModelProviderProfile, ...]:
        """Return all profiles whose capability hints mark them local-only."""
        return tuple(
            profile for profile in self._profiles.values() if profile.capability_hints.local_only
        )

    def find_with_feature(
        self,
        feature: str,
    ) -> tuple[ModelProviderProfile, ...]:
        """Return profiles declaring ``feature`` (streaming/tools/vision/audio/...).

        Unknown ``feature`` names raise :class:`ProviderValidationError`.
        """
        allowed = {
            "streaming", "tools", "vision", "audio", "embeddings",
            "model_listing", "custom_base_url",
        }
        if feature not in allowed:
            raise ProviderValidationError(
                f"unknown feature: {feature!r}; allowed: {sorted(allowed)}"
            )
        return tuple(profile for profile in self._profiles.values() if profile.supports(feature))  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_profile(self, profile: ModelProviderProfile) -> None:
        """Raise :class:`ProviderValidationError` if ``profile`` is invalid.

        Delegates to Pydantic v2 ``model_validate`` to catch shape,
        type, and constraint violations. This method exists so
        callers can check a candidate profile without first
        registering it.
        """
        if not isinstance(profile, ModelProviderProfile):
            raise ProviderValidationError(
                f"profile must be a ModelProviderProfile, got {type(profile).__name__}"
            )
        try:
            ModelProviderProfile.model_validate(profile.model_dump())
        except Exception as exc:  # noqa: BLE001 - re-raised with consistent type
            raise ProviderValidationError(str(exc)) from exc

    # ------------------------------------------------------------------
    # Mutation helpers (mostly for tests)
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Remove every registered profile.

        Intended for test fixtures. Production code should never
        call this — the registry is meant to be built up once at
        startup and then queried.
        """
        self._profiles.clear()
        self._aliases.clear()

    # ------------------------------------------------------------------
    # Built-in loading
    # ------------------------------------------------------------------

    def load_builtin_profiles(self, source: str | Path | None = None) -> int:
        """Load built-in profiles from ``providers/defaults.yaml``.

        Parameters
        ----------
        source:
            Path to a YAML file with the same shape as the shipped
            ``providers/defaults.yaml``. When ``None``, the default
            file shipped with LoopOS is used.

        Returns
        -------
        int
            Number of profiles loaded and registered.

        Raises
        ------
        FileNotFoundError
            If ``source`` does not exist.
        ProviderValidationError
            If a YAML entry fails to validate as a
            :class:`ModelProviderProfile`.
        """
        path = Path(source) if source is not None else _default_yaml_path()
        if not path.exists():
            raise FileNotFoundError(f"provider defaults file not found: {path}")

        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise RuntimeError("PyYAML is required to load built-in provider profiles") from exc

        with path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}

        if not isinstance(payload, dict):
            raise ProviderValidationError(
                f"{path}: top-level YAML must be a mapping, got {type(payload).__name__}"
            )
        entries = payload.get("providers")
        if not isinstance(entries, list):
            raise ProviderValidationError(
                f"{path}: 'providers' must be a list, got {type(entries).__name__}"
            )

        loaded = 0
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            profile = _profile_from_yaml_entry(entry)
            if profile is None:
                continue
            try:
                self.register(profile)
            except DuplicateProviderError as exc:
                # Defensive: the shipped YAML has unique provider_ids, but
                # a user-supplied YAML may not. Surface a clear error.
                raise ProviderValidationError(
                    f"{path}: duplicate provider_id {exc.provider_id!r}"
                ) from exc
            loaded += 1
        return loaded

    # ------------------------------------------------------------------
    # Repr / introspection
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._profiles)

    def __contains__(self, provider_id: object) -> bool:
        return isinstance(provider_id, str) and self.contains(provider_id)

    def __repr__(self) -> str:
        return f"ProviderRegistry(profiles={len(self._profiles)})"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _default_yaml_path() -> Path:
    """Return the path to the shipped ``providers/defaults.yaml``."""
    return Path(__file__).resolve().parent.parent.parent / "providers" / "defaults.yaml"


def _profile_from_yaml_entry(entry: dict[str, Any]) -> ModelProviderProfile | None:
    """Translate a single YAML entry into a :class:`ModelProviderProfile`.

    Returns ``None`` when the entry is missing a usable ``id``.
    """
    raw_id = entry.get("id")
    if not isinstance(raw_id, str) or not raw_id.strip():
        return None
    provider_id = raw_id.strip().lower()

    # Pull capability hints straight from the (already-merged) entry.
    capabilities = entry.get("capabilities") or ["text"]
    cost_class = entry.get("cost_class", "unknown")
    latency_class = entry.get("latency_class", "unknown")
    reliability_score = entry.get("reliability_score", 0.5)
    local_only = bool(entry.get("local_only", False))

    aliases = entry.get("aliases") or []
    if isinstance(aliases, str):
        aliases = [aliases]
    default_models = entry.get("default_models") or []
    if isinstance(default_models, str):
        default_models = [default_models]

    # Infer kind. Local providers override the table.
    if local_only or provider_id in ("huggingface", "ollama-cloud"):
        kind: ProviderKind = "local_openai_compatible"
    else:
        kind = _KIND_BY_PROVIDER_ID.get(provider_id, "openai_compatible")

    auth_modes: tuple[str, ...]
    if local_only:
        auth_modes = ("none",)
    elif kind == "bedrock":
        auth_modes = ("aws_sdk",)
    else:
        auth_modes = ("api_key",)

    base_url_required = (
        kind in ("custom_openai_compatible", "local_openai_compatible")
        or provider_id == "ollama-cloud"
    )

    notes = entry.get("notes", "") or ""

    # Declare capability-aligned feature flags so the registry's
    # ``find_with_feature`` reflects the YAML capability hints.
    capabilities_set = {str(c).strip().lower() for c in capabilities if isinstance(c, str)}
    supports_vision = "vision" in capabilities_set
    supports_embeddings = "embeddings" in capabilities_set
    supports_tools = "tools" in capabilities_set or kind in (
        "openai_compatible", "anthropic_messages", "gemini"
    )

    return ModelProviderProfile(
        provider_id=provider_id,
        name=_humanize(provider_id),
        aliases=tuple(str(a).strip() for a in aliases if str(a).strip()),
        kind=kind,
        api_style="chat_completions",
        auth_modes=auth_modes,
        base_url_required=base_url_required,
        supports_streaming=True,
        supports_tools=supports_tools,
        supports_vision=supports_vision,
        supports_audio=False,
        supports_embeddings=supports_embeddings,
        supports_model_listing=True,
        supports_custom_base_url=True,
        default_models=tuple(str(m).strip() for m in default_models if str(m).strip()),
        notes=str(notes) if notes else "",
        capability_hints={
            "capabilities": tuple(capabilities),
            "cost_class": str(cost_class),
            "latency_class": str(latency_class),
            "reliability_score": float(reliability_score),
            "local_only": local_only,
        },
    )


def _humanize(provider_id: str) -> str:
    """Best-effort human-readable name from a provider_id."""
    return provider_id.replace("-", " ").replace("_", " ").title()
