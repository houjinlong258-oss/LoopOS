"""Typed contracts for the LoopOS Provider Runtime Registry.

This module defines the **metadata-only** provider contract that the
:mod:`loopos.providers.registry` registry holds. It is a v0.2
substrate; it does not construct HTTP clients, probe live model
catalogs, or schedule inference calls — those concerns live in
:mod:`loopos.model_kernel` and the future transport layer.

Design provenance
-----------------

The **shape** of this contract is borrowed from Hermes Agent's
``ProviderProfile`` dataclass (MIT, © 2025 Nous Research). The
**specific code** is a clean-room reimplementation: every field is
re-expressed through LoopOS's Pydantic v2 + ``ConfigDict(extra="forbid")``
+ ``Literal`` enum style, every hook slot is a typed stub, and no
line of Hermes source is copied. See
``docs/source-transplant/license-and-provenance-audit.md`` for the
provenance record.

Distinction from :mod:`loopos.model_kernel`
-------------------------------------------

LoopOS already ships :mod:`loopos.model_kernel` with its own
``ProviderProfile`` and ``ProviderRegistry``. The two coexist by
design:

* ``loopos.model_kernel.ProviderRegistry`` is the **scheduler-aware**
  runtime registry: it routes requests, runs ``MultiModelScheduler``,
  and fronts ``MockModelClient`` / ``OpenAICompatibleClient``.

* ``loopos.providers.ProviderRegistry`` is the **metadata-only**
  substrate: it stores declared capabilities, auth modes, endpoints,
  and hook slots without performing any inference. Future v0.3+
  layers (model router, capability-boundary enforcer, transport
  adapter) can read from ``loopos.providers`` without inheriting
  scheduler or client concerns.

The two modules do not import from each other.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Enum-like Literal aliases
# ---------------------------------------------------------------------------

ProviderKind = Literal[
    "openai_compatible",
    "anthropic_messages",
    "gemini",
    "bedrock",
    "azure_ai_foundry",
    "custom_openai_compatible",
    "local_openai_compatible",
]
"""Transport family of a provider profile.

The v0.2 registry stores this as metadata only — no transport is
implemented here. v0.3+ will route per-kind in the transport layer.
"""

ProviderAuthMode = Literal[
    "api_key",
    "oauth_external",
    "aws_sdk",
    "none",
]
"""How the transport layer should authenticate with the provider.

``none`` is reserved for local / no-credential providers (Ollama,
LM Studio). It does not mean the provider is unauthenticated by
default; it means the transport should not look for credentials.
"""

CostClass = Literal["unknown", "low", "medium", "high", "local"]
LatencyClass = Literal["unknown", "low", "medium", "high"]

ModelCapability = Literal[
    "text",
    "reasoning",
    "coding",
    "tools",
    "vision",
    "audio",
    "embeddings",
    "local",
]
"""Declared capability of a model provider profile.

This set is intentionally narrower than
:data:`loopos.model_kernel.models.ProviderCapability` because the
v0.2 registry only consumes the capabilities needed for routing
decisions and policy checks. The model_kernel capability set
covers more transport-level flags (json_schema, long_context,
streaming, low_cost, high_reliability, video) that the metadata
registry does not need to assert.
"""

_ALLOWED_CAPABILITY_VALUES: frozenset[str] = frozenset(
    {"text", "reasoning", "coding", "tools", "vision", "audio", "embeddings", "local"}
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class ProviderCapabilityHints(BaseModel):
    """Structured capability block attached to a provider profile.

    Mirrors the YAML anchor structure in ``providers/defaults.yaml``:
    the five base anchors (``text``, ``reasoning``, ``coding``,
    ``vision``, ``local``) provide the canonical capability sets;
    per-profile entries override or extend them.
    """

    model_config = ConfigDict(extra="forbid")

    capabilities: tuple[ModelCapability, ...] = Field(
        default_factory=lambda: ("text",),
        description="Declared capabilities of this provider profile.",
    )
    cost_class: CostClass = "unknown"
    latency_class: LatencyClass = "unknown"
    reliability_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Provider reliability hint; 1.0 = production-grade.",
    )
    local_only: bool = Field(
        default=False,
        description="True if this provider runs entirely on the local host.",
    )

    @field_validator("capabilities", mode="before")
    @classmethod
    def _validate_capabilities(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ("text",)
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, (list, tuple)):
            raise ValueError("capabilities must be a list of capability strings")
        cleaned: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("capability entries must be strings")
            token = item.strip().lower()
            if not token:
                raise ValueError("capability entries must be non-empty")
            if token not in _ALLOWED_CAPABILITY_VALUES:
                raise ValueError(f"unknown capability: {token!r}")
            if token not in cleaned:
                cleaned.append(token)
        return tuple(cleaned)


# ---------------------------------------------------------------------------
# Top-level contract
# ---------------------------------------------------------------------------


class ModelProviderProfile(BaseModel):
    """Declarative metadata for a single model provider.

    A profile declares **what a provider is** — identity, auth,
    endpoint shape, capabilities, declared feature flags, default
    models — without **how it is called**. The transport layer
    (out of v0.2 scope) reads from a profile and turns it into an
    actual inference call.

    The contract is designed to be:

    * **Strict:** ``extra='forbid'`` everywhere; no silent drops.
    * **JSON-safe:** ``to_json()`` / ``from_json()`` round-trip
      any profile.
    * **Deterministic:** no timestamps with sub-second resolution,
      no implicit defaults that change between runs.
    * **Replayable:** the same input always yields the same profile.

    Required fields: ``provider_id``, ``name``, ``kind``,
    ``capability_hints``.
    """

    model_config = ConfigDict(extra="forbid")

    # ---- identity --------------------------------------------------------
    provider_id: str = Field(
        ...,
        description=(
            "Canonical, kebab-case identifier (e.g. 'openai', 'anthropic'). "
            "Used as the primary registry key. Must be unique within a registry."
        ),
    )
    name: str = Field(
        ...,
        description="Human-readable display name (e.g. 'OpenAI', 'Anthropic').",
    )
    aliases: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Alternate provider_id values the registry will accept.",
    )

    # ---- transport classification ----------------------------------------
    kind: ProviderKind = Field(
        ...,
        description="Transport family this provider belongs to.",
    )
    api_style: str = Field(
        default="chat_completions",
        description="Specific API dialect within the kind (chat_completions, responses, messages, ...).",
    )

    # ---- auth & endpoint -------------------------------------------------
    auth_modes: tuple[ProviderAuthMode, ...] = Field(
        default_factory=lambda: ("api_key",),
        description="Authentication modes supported by this provider.",
    )
    base_url_required: bool = Field(
        default=False,
        description=(
            "True if the provider cannot function without a user-supplied base_url. "
            "Custom OpenAI-compatible and local providers must set this True; the "
            "validator enforces it."
        ),
    )
    default_base_url: str = Field(
        default="",
        description="Optional default base URL; transport may override.",
    )

    # ---- declared feature flags -----------------------------------------
    supports_streaming: bool = True
    supports_tools: bool = True
    supports_vision: bool = False
    supports_audio: bool = False
    supports_embeddings: bool = False
    supports_model_listing: bool = True
    """True if the provider exposes a catalog endpoint that lists live models.

    The v0.2 registry does NOT call this endpoint; the flag is purely
    declarative so v0.3+ transport layers know whether ``fetch_models()``
    is meaningful for this provider.
    """
    supports_custom_base_url: bool = True

    # ---- model catalog metadata -----------------------------------------
    default_models: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Built-in placeholder model identifiers (no live discovery).",
    )
    model_aliases: dict[str, str] = Field(
        default_factory=dict,
        description="Map from user-friendly alias to canonical model id.",
    )
    context_window: int | None = Field(
        default=None,
        ge=1,
        description="Default maximum token count for models from this provider, if known.",
    )

    # ---- provenance & governance ----------------------------------------
    notes: str = Field(
        default="",
        description="Free-form documentation string; surfaced in CLI help.",
    )
    capability_hints: ProviderCapabilityHints = Field(
        default_factory=ProviderCapabilityHints,
        description="Structured capability block (see ProviderCapabilityHints).",
    )

    # ---- bookkeeping -----------------------------------------------------
    profile_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier of this profile instance; not the provider_id.",
    )
    created_at: datetime = Field(default_factory=_utc_now)

    # ---- validators ------------------------------------------------------

    @field_validator("provider_id", "name", "kind")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("value is required and must be non-empty")
        return value

    @field_validator("provider_id")
    @classmethod
    def provider_id_canonical(cls, value: str) -> str:
        """Lower-case the provider_id; canonicalize hyphens to underscores internally."""
        return value.strip().lower()

    @field_validator("auth_modes", mode="before")
    @classmethod
    def _validate_auth_modes(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ("api_key",)
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, (list, tuple)):
            raise ValueError("auth_modes must be a list of auth mode strings")
        allowed = {"api_key", "oauth_external", "aws_sdk", "none"}
        cleaned: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("auth mode entries must be strings")
            token = item.strip().lower()
            if token not in allowed:
                raise ValueError(f"unknown auth mode: {token!r}")
            if token not in cleaned:
                cleaned.append(token)
        return tuple(cleaned)

    @model_validator(mode="after")
    def _enforce_kind_local_consistency(self) -> "ModelProviderProfile":
        """Local providers must be marked ``local_only`` and may have no auth."""
        if self.kind in ("local_openai_compatible",) and not self.capability_hints.local_only:
            object.__setattr__(self.capability_hints, "local_only", True)
        if self.capability_hints.local_only and "api_key" in self.auth_modes and len(self.auth_modes) == 1:
            # A local provider is allowed to declare api_key auth in addition to none,
            # but a local-only provider with no other auth is the canonical shape.
            pass
        return self

    @model_validator(mode="after")
    def _enforce_custom_base_url(self) -> "ModelProviderProfile":
        """Custom OpenAI-compatible providers must require a base URL."""
        if self.kind in ("custom_openai_compatible", "local_openai_compatible") and not self.base_url_required:
            object.__setattr__(self, "base_url_required", True)
        return self

    # ---- capability helpers ---------------------------------------------

    def has_capability(self, capability: ModelCapability) -> bool:
        """Return True if this profile declares ``capability``."""
        return capability in self.capability_hints.capabilities

    def matches(self, capability: ModelCapability) -> bool:
        """Alias for :meth:`has_capability` (matches the registry API)."""
        return self.has_capability(capability)

    def supports(self, feature: Literal[
        "streaming", "tools", "vision", "audio", "embeddings", "model_listing", "custom_base_url"
    ]) -> bool:
        """Return True if this profile declares the given feature."""
        return {
            "streaming": self.supports_streaming,
            "tools": self.supports_tools,
            "vision": self.supports_vision,
            "audio": self.supports_audio,
            "embeddings": self.supports_embeddings,
            "model_listing": self.supports_model_listing,
            "custom_base_url": self.supports_custom_base_url,
        }[feature]

    # ---- (de)serialization ----------------------------------------------

    def to_json(self) -> str:
        """Stable JSON representation (no ``None`` stripping)."""
        return self.model_dump_json(exclude_none=False)

    @classmethod
    def from_json(cls, raw: str | bytes | dict[str, Any]) -> "ModelProviderProfile":
        """Inverse of :meth:`to_json`."""
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        if isinstance(raw, str):
            import json
            data = json.loads(raw)
        else:
            data = raw
        return cls.model_validate(data)
