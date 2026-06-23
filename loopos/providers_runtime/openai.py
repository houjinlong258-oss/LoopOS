"""OpenAI-compatible Provider Runtime.

The :class:`OpenAICompatibleProviderRuntime` constructs an
OpenAI-style chat completion request and (when explicitly enabled)
issues it over HTTP. **Live calls are disabled by default.** The
runtime accepts a ``transport`` callable so tests can inject a fake
HTTP client without depending on ``requests`` / ``httpx``.

The transport contract is intentionally minimal:

    transport(request: PreparedRequest) -> PreparedResponse

where :class:`PreparedRequest` and :class:`PreparedResponse` are
defined in this module. The default transport raises
``ProviderConfigError`` so the runtime fails closed when no
injection is provided.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Iterable

from pydantic import BaseModel, ConfigDict, Field

from loopos.providers_runtime.base import (
    ProviderInfo,
    REASON_CONFIG_MISSING,
    StreamingChunk,
    blocked_response,
    dry_run_response,
)
from loopos.providers_runtime.errors import ProviderConfigError
from loopos.providers_runtime.models import (
    ModelCallRequest,
    ModelCallResponse,
    ModelUsage,
)
from loopos.providers_runtime.usage import redact_secrets


DEFAULT_BASE_URL = "https://api.openai.com/v1"


class PreparedRequest(BaseModel):
    """Transport-agnostic description of a request to send."""

    model_config = ConfigDict(extra="forbid")

    method: str
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    body: dict[str, Any] = Field(default_factory=dict)


class PreparedResponse(BaseModel):
    """Transport-agnostic description of a response to feed back."""

    model_config = ConfigDict(extra="forbid")

    status: int
    headers: dict[str, str] = Field(default_factory=dict)
    body: dict[str, Any] = Field(default_factory=dict)
    text: str = ""


# A transport is a callable that takes a PreparedRequest and returns a
# PreparedResponse. Tests inject fakes; production wires httpx/requests.
Transport = Callable[[PreparedRequest], PreparedResponse]


def _default_transport(_request: PreparedRequest) -> PreparedResponse:  # pragma: no cover
    raise ProviderConfigError(
        "OpenAICompatibleProviderRuntime has no default transport; "
        "either pass transport=... or use --dry-run"
    )


class OpenAICompatibleProviderRuntime:
    """OpenAI-style chat completion provider runtime."""

    provider_id: str = "openai"
    display_name: str = "OpenAI-compatible Provider"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        transport: Transport | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self._explicit_transport = transport
        self.last_prepared: PreparedRequest | None = None

    def info(self) -> ProviderInfo:
        configured = bool(self._api_key) or bool(os.environ.get("OPENAI_API_KEY"))
        return ProviderInfo(
            provider_id=self.provider_id,
            display_name=self.display_name,
            kind="openai_compatible",
            env_key="OPENAI_API_KEY",
            base_url=self._base_url,
            configured=configured,
            live_calls_default=False,
            notes="OpenAI-compatible; live calls disabled by default",
        )

    def _build_request(
        self,
        request: ModelCallRequest,
        *,
        with_auth: bool,
    ) -> PreparedRequest:
        body: dict[str, Any] = {
            "model": request.model_id,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            body["max_tokens"] = request.max_tokens
        if request.json_schema is not None:
            body["response_format"] = {"type": "json_schema", "schema": request.json_schema}
        if request.stream:
            body["stream"] = True
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if with_auth:
            api_key = self._api_key or os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ProviderConfigError(
                    "OpenAICompatibleProviderRuntime: OPENAI_API_KEY not set"
                )
            # NOTE: do NOT put the real key in this PreparedRequest.
            # ``call()`` injects the real Authorization header after
            # the call site has decided to actually go live, and it
            # then redacts the header before storing ``last_prepared``.
            # Putting the real key here would leak it through
            # ``last_prepared.model_dump_json()`` and any log/trace
            # that follows.
            headers["Authorization"] = "Bearer ***REDACTED***"
        return PreparedRequest(
            method="POST",
            url=f"{self._base_url}/chat/completions",
            headers=headers,
            body=body,
        )

    def _parse_response(
        self,
        request: ModelCallRequest,
        response: PreparedResponse,
    ) -> ModelCallResponse:
        if response.status >= 400:
            return ModelCallResponse(
                request_id=request.request_id,
                provider_id=self.provider_id,
                model_id=request.model_id,
                status="failed",
                content=None,
                reason_codes=[
                    f"http_{response.status}",
                    redact_secrets(response.text)[:200] or "openai_http_error",
                ],
            )
        body = response.body or {}
        try:
            choice = (body.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            content = message.get("content") or ""
            usage_raw = body.get("usage") or {}
            usage = ModelUsage(
                prompt_tokens=int(usage_raw.get("prompt_tokens", 0) or 0),
                completion_tokens=int(usage_raw.get("completion_tokens", 0) or 0),
                total_tokens=int(usage_raw.get("total_tokens", 0) or 0),
                estimated_cost_usd=0.0,
            )
        except Exception as exc:  # noqa: BLE001 - bad payload
            return ModelCallResponse(
                request_id=request.request_id,
                provider_id=self.provider_id,
                model_id=request.model_id,
                status="failed",
                content=None,
                reason_codes=["openai_response_parse_error", str(exc)[:200]],
            )
        return ModelCallResponse(
            request_id=request.request_id,
            provider_id=self.provider_id,
            model_id=request.model_id,
            status="completed",
            content=content,
            tool_calls=message.get("tool_calls") or [],
            usage=usage,
            reason_codes=["openai_completed"],
        )

    def call(self, request: ModelCallRequest) -> ModelCallResponse:
        if not request.live_provider_calls_allowed:
            return dry_run_response(request)
        # Re-attach the real Authorization header (we masked it in
        # _build_request so the prepared object never contains the
        # raw key in tests / logs).
        api_key = self._api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return blocked_response(
                request,
                reason_codes=[REASON_CONFIG_MISSING, "OPENAI_API_KEY not set"],
            )
        try:
            prepared = self._build_request(request, with_auth=True)
        except ProviderConfigError as exc:
            return blocked_response(
                request,
                reason_codes=[REASON_CONFIG_MISSING, str(exc)[:200]],
            )
        prepared.headers["Authorization"] = f"Bearer {api_key}"
        # Build a redacted copy for storage. ``last_prepared`` is
        # a Pydantic model that callers may ``model_dump_json()`` and
        # log; storing the real key there would leak it. We retain
        # the original (with the real key) for this call only.
        redacted_for_log = prepared.model_copy(deep=True)
        redacted_for_log.headers["Authorization"] = "Bearer ***REDACTED***"
        self.last_prepared = redacted_for_log
        transport = self._explicit_transport or _default_transport
        try:
            response = transport(prepared)
        except ProviderConfigError as exc:
            return blocked_response(
                request,
                reason_codes=[REASON_CONFIG_MISSING, str(exc)[:200]],
            )
        except Exception as exc:  # noqa: BLE001 - transport error
            return ModelCallResponse(
                request_id=request.request_id,
                provider_id=self.provider_id,
                model_id=request.model_id,
                status="failed",
                content=None,
                reason_codes=["provider_transport_error", str(exc)[:200]],
            )
        return self._parse_response(request, response)

    def stream(self, request: ModelCallRequest) -> Iterable[StreamingChunk]:
        # Streaming reuses call() and yields a single terminal chunk;
        # the runtime never opens an SSE stream unless an explicit
        # transport supports it.
        response = self.call(request)
        yield StreamingChunk(
            request_id=request.request_id,
            provider_id=self.provider_id,
            model_id=request.model_id,
            delta=response.content or "",
            done=response.status != "completed",
            finish_reason="stop" if response.status == "completed" else "error",
            usage=response.usage,
        )


__all__ = [
    "OpenAICompatibleProviderRuntime",
    "PreparedRequest",
    "PreparedResponse",
    "Transport",
    "DEFAULT_BASE_URL",
]
