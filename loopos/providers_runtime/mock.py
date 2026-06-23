"""Mock Provider Runtime — deterministic, network-free.

The :class:`MockProviderRuntime` is the reference runtime used by the
test suite and the Workbench dry-run. It echoes the request back as a
structured response and never touches the network.
"""

from __future__ import annotations

from typing import Iterable

from loopos.providers_runtime.base import (
    ProviderInfo,
    StreamingChunk,
)
from loopos.providers_runtime.models import (
    ModelCallRequest,
    ModelCallResponse,
    ModelUsage,
)


class MockProviderRuntime:
    """Deterministic mock provider runtime."""

    provider_id: str = "mock"
    display_name: str = "Mock Provider Runtime"

    def __init__(self) -> None:
        self.call_log: list[ModelCallRequest] = []
        self.stream_log: list[ModelCallRequest] = []

    def info(self) -> ProviderInfo:
        return ProviderInfo(
            provider_id=self.provider_id,
            display_name=self.display_name,
            kind="mock",
            env_key="",
            base_url="",
            configured=True,
            live_calls_default=False,
            notes="deterministic network-free runtime; used in tests and dry-run",
        )

    def _echo_response(self, request: ModelCallRequest) -> ModelCallResponse:
        # Concatenate the user-prompt content as a deterministic reply.
        reply = "\n".join(
            f"[{m.role}] {m.content}" for m in request.messages
        )
        prompt_tokens = max(1, sum(len(m.content) for m in request.messages) // 4)
        completion_tokens = max(1, len(reply) // 4)
        return ModelCallResponse(
            request_id=request.request_id,
            provider_id=self.provider_id,
            model_id=request.model_id,
            status="completed",
            content=reply,
            tool_calls=[],
            usage=ModelUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                estimated_cost_usd=0.0,
            ),
            reason_codes=["mock_provider"],
        )

    def call(self, request: ModelCallRequest) -> ModelCallResponse:
        self.call_log.append(request)
        if not request.live_provider_calls_allowed:
            # No live call needed; return the echo anyway since the mock
            # is in-process. This is what makes the mock safe to use in
            # the Workbench dry-run.
            response = self._echo_response(request)
            response.reason_codes = ["mock_provider", "live_provider_disabled"]
            return response
        return self._echo_response(request)

    def stream(self, request: ModelCallRequest) -> Iterable[StreamingChunk]:
        self.stream_log.append(request)
        response = self._echo_response(request)
        # Emit a single chunk and a done chunk. Deterministic.
        yield StreamingChunk(
            request_id=request.request_id,
            provider_id=self.provider_id,
            model_id=request.model_id,
            delta=response.content or "",
            done=False,
        )
        yield StreamingChunk(
            request_id=request.request_id,
            provider_id=self.provider_id,
            model_id=request.model_id,
            delta="",
            done=True,
            finish_reason="stop",
            usage=response.usage,
        )


__all__ = ["MockProviderRuntime"]
