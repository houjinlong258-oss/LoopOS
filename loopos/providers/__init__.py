"""Provider Runtime Registry for LoopOS v0.2.

This package owns the **metadata-only** registry of model provider
profiles. It does NOT make network calls, does NOT instantiate HTTP
clients, and does NOT probe providers for live model lists.

Public surface
--------------

* :class:`ModelProviderProfile` — declarative provider metadata
  (Pydantic v2, ``ConfigDict(extra="forbid")``).
* :class:`ProviderCapabilityHints` — structured capability block.
* :class:`ProviderRegistry` — in-memory registry with explicit
  ``register`` / ``get`` / ``list`` / ``find_by_capability`` /
  ``validate_profile`` / ``load_builtin_profiles`` API.
* Enum aliases: :data:`ProviderKind`, :data:`ProviderAuthMode`,
  :data:`ModelCapability`, :data:`CostClass`, :data:`LatencyClass`.
* Exception hierarchy: :class:`ProviderError`,
  :class:`ProviderNotFoundError`, :class:`DuplicateProviderError`,
  :class:`ProviderValidationError`.

Design provenance
-----------------

The **shape** of the contract is borrowed from Hermes Agent's
``ProviderProfile`` dataclass (MIT, © 2025 Nous Research, see
``docs/source-transplant/license-and-provenance-audit.md``). No
line of Hermes code is copied; every field is re-expressed through
LoopOS's Pydantic v2 + ``Literal`` enum conventions.

The **built-in profile catalog** is loaded from the shipped
``providers/defaults.yaml`` file. That file is the canonical LoopOS
data source for provider metadata.

Coexistence with :mod:`loopos.model_kernel`
-------------------------------------------

LoopOS already ships :mod:`loopos.model_kernel` with its own
``ProviderProfile`` / ``ProviderRegistry``. The two modules
coexist:

* ``loopos.model_kernel`` is the **scheduler-aware** runtime
  registry; it routes inference calls and operates clients.
* ``loopos.providers`` is the **metadata-only** substrate above;
  it stores declarative contracts without performing inference.

The two modules do not import from each other.
"""

from loopos.providers.errors import (
    DuplicateProviderError,
    ProviderError,
    ProviderNotFoundError,
    ProviderValidationError,
)
from loopos.providers.models import (
    CostClass,
    LatencyClass,
    ModelCapability,
    ModelProviderProfile,
    ProviderAuthMode,
    ProviderCapabilityHints,
    ProviderKind,
)
from loopos.providers.registry import ProviderRegistry

__all__ = [
    "CostClass",
    "DuplicateProviderError",
    "LatencyClass",
    "ModelCapability",
    "ModelProviderProfile",
    "ProviderAuthMode",
    "ProviderCapabilityHints",
    "ProviderError",
    "ProviderKind",
    "ProviderNotFoundError",
    "ProviderRegistry",
    "ProviderValidationError",
]
