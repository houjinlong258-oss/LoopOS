"""OpenAI-compatible provider boundary for LoopOS.

Provides a safe client boundary for any OpenAI API-compatible endpoint
without calling real APIs in tests. All provider calls must be routed
through the provider syscall/policy path.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OpenAICompatibleConfig(BaseModel):
    """Configuration for an OpenAI-compatible provider endpoint."""

    provider_id: str = "openai"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4"
    organization: str | None = None
    timeout_seconds: float = 30.0
    max_retries: int = 2

    @property
    def is_available(self) -> bool:
        """API key must be set for the provider to be available."""
        return bool(self.api_key and self.api_key.strip())


class ChatMessage(BaseModel):
    """OpenAI-compatible chat message."""
    role: Literal["system", "user", "assistant", "tool"] = "user"
    content: str = ""
    name: str | None = None


class ChatCompletionRequest(BaseModel):
    """Request payload for chat completions."""
    model: str
    messages: list[ChatMessage]
    temperature: float = 0.7
    max_tokens: int | None = None
    top_p: float | None = None
    stop: list[str] | None = None
    stream: bool = False


class ChatCompletionChoice(BaseModel):
    """A single completion choice."""
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class ChatCompletionUsage(BaseModel):
    """Token usage statistics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    """Response from a chat completion endpoint."""
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid4().hex[:12]}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp()))
    model: str = ""
    choices: list[ChatCompletionChoice] = Field(default_factory=list)
    usage: ChatCompletionUsage = Field(default_factory=ChatCompletionUsage)


class ProviderError(BaseModel):
    """Normalized provider error."""
    status_code: int = 500
    error_type: str = "internal_error"
    message: str = ""
    provider_id: str = ""


class OpenAICompatibleClient:
    """Client boundary for OpenAI-compatible APIs.

    This client does NOT make real HTTP calls.
    It builds request payloads and parses response payloads.
    Actual transport is delegated to the syscall/provider gateway.
    """

    def __init__(self, config: OpenAICompatibleConfig) -> None:
        self.config = config

    @property
    def is_available(self) -> bool:
        return self.config.is_available

    def build_request(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Build a request payload dict ready for transport."""
        if not self.is_available:
            raise RuntimeError(f"Provider {self.config.provider_id} is not available (missing API key)")

        chat_messages = [ChatMessage(**m) for m in messages]
        request = ChatCompletionRequest(
            model=model or self.config.model,
            messages=chat_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return {
            "url": f"{self.config.base_url}/chat/completions",
            "headers": {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                **({"OpenAI-Organization": self.config.organization}
                   if self.config.organization else {}),
            },
            "body": request.model_dump(mode="json", exclude_none=True),
        }

    def parse_response(self, raw: dict[str, Any]) -> ChatCompletionResponse:
        """Parse a raw API response into a typed ChatCompletionResponse."""
        # Handle error responses
        if "error" in raw:
            error_data = raw["error"]
            raise ProviderResponseError(
                ProviderError(
                    status_code=raw.get("status_code", 500),
                    error_type=error_data.get("type", "api_error"),
                    message=error_data.get("message", "Unknown error"),
                    provider_id=self.config.provider_id,
                )
            )
        return ChatCompletionResponse.model_validate(raw)

    def parse_error(self, raw: dict[str, Any], *, status_code: int = 500) -> ProviderError:
        """Parse an error response into a normalized ProviderError."""
        error_data = raw.get("error", raw)
        return ProviderError(
            status_code=status_code,
            error_type=error_data.get("type", "unknown"),
            message=error_data.get("message", str(raw)),
            provider_id=self.config.provider_id,
        )


class ProviderResponseError(RuntimeError):
    """Raised when the provider returns an error response."""

    def __init__(self, error: ProviderError) -> None:
        self.error = error
        super().__init__(f"[{error.provider_id}] {error.error_type}: {error.message}")
