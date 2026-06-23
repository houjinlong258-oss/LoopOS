"""Ollama Provider Runtime (local models).

The :class:`OllamaProviderRuntime` talks to a local Ollama daemon. The
daemon URL is read from ``OLLAMA_HOST`` (default
``http://localhost:11434``). The runtime is **disabled by default**
unless ``OLLAMA_HOST`` is set in the environment, but the user can
still call it in dry-run mode without a daemon.

The transport contract is the same as the OpenAI-compatible runtime:
a :class:`PreparedRequest` in, a :class:`PreparedResponse` out, so
tests can inject a fake.
"""

from __future__ import annotations

import os
from typing import Iterable

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
from loopos.providers_runtime.openai import PreparedRequest, PreparedResponse, Transport
from loopos.providers_runtime.usage import redact_secrets


DEFAULT_OLLAMA_HOST = "http://localhost:11434"


def _default_transport(_request: PreparedRequest) -> PreparedResponse:  # pragma: no cover
    raise ProviderConfigError(
        "OllamaProviderRuntime has no default transport; "
        "either pass transport=... or use --dry-run"
    )


class OllamaProviderRuntime:
    """Local Ollama runtime."""

    provider_id: str = "ollama"
    display_name: str = "Ollama Local Provider"

    def __init__(
        self,
        *,
        host: str | None = None,
        transport: Transport | None = None,
    ) -> None:
        self._host = (host or os.environ.get("OLLAMA_HOST") or DEFAULT_OLLAMA_HOST).rstrip("/")
        self._explicit_transport = transport

    def info(self) -> ProviderInfo:
        configured = bool(os.environ.get("OLLAMA_HOST")) or self._explicit_transport is not None
        return ProviderInfo(
            provider_id=self.provider_id,
            display_name=self.display_name,
            kind="ollama",
            env_key="OLLAMA_HOST",
            base_url=self._host,
            configured=configured,
            live_calls_default=True,  # Ollama is local; safe to call.
            notes="Ollama local daemon; only call when OLLAMA_HOST is set or transport injected",
        )

    def _build_request(self, request: ModelCallRequest) -> PreparedRequest:
        return PreparedRequest(
            method="POST",
            url=f"{self._host}/api/chat",
            headers={"Content-Type": "application/json"},
            body={
                "model": request.model_id,
                "messages": [{"role": m.role, "content": m.content} for m in request.messages],
                "stream": bool(request.stream),
                "options": {
                    "temperature": request.temperature,
                    **({"num_predict": request.max_tokens} if request.max_tokens else {}),
                },
            },
        )

    def _parse_response(
        self,
        request: ModelCallRequest,
        response: PreparedResponse,
    ) -> ModelCallResponse:
        body = response.body or {}
        if response.status >= 400:
            return ModelCallResponse(
                request_id=request.request_id,
                provider_id=self.provider_id,
                model_id=request.model_id,
                status="failed",
                content=None,
                reason_codes=[
                    f"http_{response.status}",
                    redact_secrets(response.text or "ollama_http_error")[:200],
                ],
            )
        message = body.get("message") or {}
        content = message.get("content") or ""
        prompt_tokens = int((body.get("prompt_eval_count") or 0))
        completion_tokens = int((body.get("eval_count") or 0))
        return ModelCallResponse(
            request_id=request.request_id,
            provider_id=self.provider_id,
            model_id=request.model_id,
            status="completed",
            content=content,
            tool_calls=[],
            usage=ModelUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                estimated_cost_usd=0.0,
            ),
            reason_codes=["ollama_completed"],
        )

    def call(self, request: ModelCallRequest) -> ModelCallResponse:
        if not request.live_provider_calls_allowed:
            return dry_run_response(request)
        prepared = self._build_request(request)
        transport = self._explicit_transport or _default_transport
        try:
            response = transport(prepared)
        except ProviderConfigError as exc:
            return blocked_response(
                request,
                reason_codes=[REASON_CONFIG_MISSING, str(exc)[:200]],
            )
        except Exception as exc:  # noqa: BLE001
            return ModelCallResponse(
                request_id=request.request_id,
                provider_id=self.provider_id,
                model_id=request.model_id,
                status="failed",
                content=None,
                reason_codes=["ollama_transport_error", redact_secrets(str(exc))[:200]],
            )
        return self._parse_response(request, response)

    def stream(self, request: ModelCallRequest) -> Iterable[StreamingChunk]:
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


__all__ = ["OllamaProviderRuntime", "DEFAULT_OLLAMA_HOST"]
