"""LoopOS v0.3 Real LLM Provider Runtime.

This package adds the **governed** transport layer that turns a
:class:`~loopos.providers_runtime.models.ModelCallRequest` into a real
model call. Unlike :mod:`loopos.providers` (metadata-only), this package
can construct HTTP requests and (for local Ollama) talk to a local
endpoint — but every live call is gated:

* live calls are **disabled by default**;
* a live call requires explicit ``live_provider_calls_allowed=True``;
* a live call requires a configured API key / endpoint;
* a live call requires a budget; the :class:`ProviderBudget` guard
  blocks the request when the budget is exceeded;
* secrets are never written to the trace, logs, or error messages.
"""

from __future__ import annotations

from loopos.providers_runtime.budget import ProviderBudget, BudgetDecision
from loopos.providers_runtime.errors import (
    ProviderRuntimeError,
    ProviderConfigError,
    ProviderBudgetError,
)
from loopos.providers_runtime.models import (
    ModelCallRequest,
    ModelCallResponse,
    ModelMessage,
    ModelUsage,
)
from loopos.providers_runtime.base import ProviderRuntime
from loopos.providers_runtime.mock import MockProviderRuntime
from loopos.providers_runtime.openai import OpenAICompatibleProviderRuntime
from loopos.providers_runtime.ollama import OllamaProviderRuntime
from loopos.providers_runtime.registry import ProviderRuntimeRegistry
from loopos.providers_runtime.usage import redact_secrets

__all__ = [
    "ProviderBudget",
    "BudgetDecision",
    "ProviderRuntimeError",
    "ProviderConfigError",
    "ProviderBudgetError",
    "ModelCallRequest",
    "ModelCallResponse",
    "ModelMessage",
    "ModelUsage",
    "ProviderRuntime",
    "MockProviderRuntime",
    "OpenAICompatibleProviderRuntime",
    "OllamaProviderRuntime",
    "ProviderRuntimeRegistry",
    "redact_secrets",
]
