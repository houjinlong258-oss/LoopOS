"""Provider binding sub-models for the Agent Command Interface.

This module groups the small Pydantic models that carry the
provider-binding surface introduced in the Phase S Provider Runtime
Registry:

* :class:`CommandCapability` - capability hints declared by the
  agent for a single command.
* :class:`RiskHint` - risk signal declared by the agent for a
  command.
* :class:`ProviderHint` - declarative hint about which provider
  profile the agent would like the runner to use.
* :class:`ResolvedProvider` - the resolved outcome of
  :class:`ProviderHint` resolution.

These models are imported by :mod:`loopos.aci.models` (for the
top-level :class:`AgentCommand` and :class:`AgentCommandResult`),
by :mod:`loopos.aci.runner` (for resolution and result building),
and by :mod:`loopos.aci.provider_binding` (for the strict
``ProviderResolutionError`` boundary).

They are re-exported from :mod:`loopos.aci.models` so existing
imports of the form ``from loopos.aci.models import ProviderHint``
keep working unchanged.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Provider binding taxonomy
# ---------------------------------------------------------------------------

ProviderResolutionSource = Literal[
    "exact",
    "capability",
    "local",
    "kind",
    "default",
    "none",
]

RiskHintLevel = Literal["low", "medium", "high", "blocked", "unknown"]


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class CommandCapability(BaseModel):
    """Capability hints declared by the agent for a command.

    The runner cross-checks these against the runtime capability
    boundary. A mismatch produces a structured denial, never a
    silent override.
    """

    model_config = ConfigDict(extra="forbid")

    filesystem_read: bool = False
    filesystem_write: bool = False
    network: bool = False
    database: bool = False
    tags: list[str] = Field(default_factory=list)


class ProviderHint(BaseModel):
    """Hint that the agent expresses about which provider to use.

    The hint is consumed by the runner via
    :class:`loopos.providers.ProviderRegistry` and resolved into a
    :class:`ResolvedProvider`. The hint is **declarative**: it
    never triggers a live API call.

    Resolution semantics:

    * ``provider_id`` is set -> exact resolution.
    * ``required_capabilities`` is non-empty -> capability lookup;
      deterministic ordering by provider_id.
    * ``local_only`` is True -> only local profiles considered.
    * ``preferred_kind`` -> filter by transport family after the
      primary lookup.
    * ``allow_fallback`` is False -> silent fallback to a different
      provider is rejected.
    * No match -> reason_code ``provider_not_found`` or
      ``provider_capability_unavailable``.
    """

    model_config = ConfigDict(extra="forbid")

    provider_id: str | None = None
    required_capabilities: list[str] = Field(default_factory=list)
    preferred_kind: str | None = None
    preferred_cost_class: str | None = None
    local_only: bool | None = None
    allow_fallback: bool = False
    notes: str = ""

    @field_validator("provider_id")
    @classmethod
    def _strip_provider_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        return cleaned or None


class ResolvedProvider(BaseModel):
    """Outcome of resolving a :class:`ProviderHint`.

    The runner fills this in :class:`AgentCommandResult.resolved_provider`
    when a hint was supplied or when ``kind == "provider_select"``.

    The ``source`` field tells the agent (and any human reviewer) how
    the resolution was made:

    * ``exact`` -- matched by ``provider_id``.
    * ``capability`` -- matched via :meth:`ProviderRegistry.find_by_capability`.
    * ``local`` -- matched via :meth:`ProviderRegistry.find_local`.
    * ``kind`` -- matched via :meth:`ProviderRegistry.find_by_kind`.
    * ``default`` -- no hint, fell back to a registry default.
    * ``none`` -- no hint supplied.
    """

    model_config = ConfigDict(extra="forbid")

    provider_id: str
    display_name: str | None = None
    kind: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    source: ProviderResolutionSource = "none"
    reason_code: str = ""


class RiskHint(BaseModel):
    """Risk signal declared by the agent for a command.

    The runner forwards this to Policy OS as part of the policy
    request subject; Policy OS remains the source of truth for the
    final risk level. The hint is never authoritative.
    """

    model_config = ConfigDict(extra="forbid")

    level: RiskHintLevel = "unknown"
    reason: str = ""
    tags: list[str] = Field(default_factory=list)


__all__ = [
    "CommandCapability",
    "ProviderHint",
    "ProviderResolutionSource",
    "ResolvedProvider",
    "RiskHint",
    "RiskHintLevel",
]