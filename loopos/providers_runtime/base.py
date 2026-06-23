"""Provider Runtime base protocol and shared helpers.

The :class:`ProviderRuntime` Protocol is the contract every concrete
provider runtime (mock, openai-compatible, ollama, ...) must satisfy.
The base class also defines the **default-deny** policy: a runtime
that has not been told ``live_provider_calls_allowed=True`` returns a
``ModelCallResponse`` with ``status="blocked"`` and the structured
``reason_codes=["live_provider_disabled"]`` before touching the
network.
"""

from __future__ import annotations

from typing import Any, Iterable, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from loopos.providers_runtime.errors import ProviderConfigError
from loopos.providers_runtime.models import (
    ModelCallRequest,
    ModelCallResponse,
    ModelUsage,
)
from loopos.providers_runtime.usage import read_api_key, redact_secrets


# Default reason codes that downstream consumers can rely on.
REASON_LIVE_DISABLED = "live_provider_disabled"
REASON_LIVE_REQUIRES_APPROVAL = "live_provider_requires_explicit_approval"
REASON_BUDGET_BLOCKED = "provider_budget_exceeded"
REASON_CONFIG_MISSING = "provider_config_missing"
REASON_PROVIDER_ERROR = "provider_runtime_error"


class ProviderInfo(BaseModel):
    """Static info a runtime exposes for ``loopos providers runtime list``."""

    model_config = ConfigDict(extra="forbid")

    provider_id: str
    display_name: str
    kind: str  # "mock" | "openai_compatible" | "ollama" | "anthropic_compatible" | ...
    env_key: str = ""
    base_url: str = ""
    configured: bool = False
    live_calls_default: bool = False
    notes: str = ""


class StreamingChunk(BaseModel):
    """A single streaming chunk from a model call.

    Providers that support streaming (e.g. OpenAI SSE, Ollama NDJSON)
    emit :class:`StreamingChunk` objects through the
    :meth:`ProviderRuntime.stream` method.
    """

    model_config = ConfigDict(extra="forbid")

    request_id: str
    provider_id: str
    model_id: str
    delta: str = ""
    done: bool = False
    finish_reason: str = ""
    usage: ModelUsage | None = None


@runtime_checkable
class ProviderRuntime(Protocol):
    """Universal contract for any real LLM provider runtime."""

    provider_id: str
    display_name: str

    def info(self) -> ProviderInfo: ...

    def call(self, request: ModelCallRequest) -> ModelCallResponse: ...

    def stream(self, request: ModelCallRequest) -> Iterable[StreamingChunk]: ...


def is_live_allowed(request: ModelCallRequest) -> bool:
    """Return True iff this request is allowed to make a network call."""
    return bool(request.live_provider_calls_allowed)


def blocked_response(
    request: ModelCallRequest,
    *,
    reason_codes: list[str],
    trace_id: str | None = None,
) -> ModelCallResponse:
    """Build a structured ``blocked`` response for a denied request."""
    return ModelCallResponse(
        request_id=request.request_id,
        provider_id=request.provider_id,
        model_id=request.model_id,
        status="blocked",
        content=None,
        tool_calls=[],
        usage=None,
        reason_codes=list(reason_codes),
        trace_id=trace_id,
    )


def dry_run_response(
    request: ModelCallRequest,
    *,
    trace_id: str | None = None,
) -> ModelCallResponse:
    """Build a structured ``dry_run`` response — no network call made."""
    # Estimate token usage from message length (rough; just for dry-run).
    total_chars = sum(len(m.content) for m in request.messages)
    estimated_prompt_tokens = max(1, total_chars // 4)
    return ModelCallResponse(
        request_id=request.request_id,
        provider_id=request.provider_id,
        model_id=request.model_id,
        status="dry_run",
        content="[dry-run] request validated; no network call made",
        tool_calls=[],
        usage=ModelUsage(
            prompt_tokens=estimated_prompt_tokens,
            completion_tokens=0,
            total_tokens=estimated_prompt_tokens,
            estimated_cost_usd=0.0,
        ),
        reason_codes=["dry_run"],
        trace_id=trace_id,
    )


def ensure_configured(provider_id: str, *, env_key: str | None = None) -> str | None:
    """Read a provider's API key from the environment.

    Returns the key string (not the value) so callers can use it for
    log/trace purposes without leaking the value. Returns ``None`` if
    the key is missing.
    """
    if not env_key:
        return None
    value = read_api_key(env_key)
    if not value:
        raise ProviderConfigError(
            f"provider {provider_id!r} requires {env_key!r} in environment"
        )
    return env_key


def _sanitise_request_for_log(request: ModelCallRequest) -> dict[str, Any]:
    """Return a request dict suitable for trace/log: secrets are redacted."""
    raw: dict[str, Any] = request.model_dump(mode="json", exclude_none=True)
    sanitised: dict[str, Any] = _recursive_redact(raw)
    return sanitised


def _recursive_redact(value: Any) -> Any:
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, dict):
        return {k: _recursive_redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_recursive_redact(item) for item in value]
    return value


__all__ = [
    "ProviderRuntime",
    "ProviderInfo",
    "StreamingChunk",
    "is_live_allowed",
    "blocked_response",
    "dry_run_response",
    "ensure_configured",
    "REASON_LIVE_DISABLED",
    "REASON_LIVE_REQUIRES_APPROVAL",
    "REASON_BUDGET_BLOCKED",
    "REASON_CONFIG_MISSING",
    "REASON_PROVIDER_ERROR",
]
