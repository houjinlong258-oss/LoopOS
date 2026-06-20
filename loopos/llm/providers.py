"""OpenAI-compatible and mock LLM providers."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Protocol

from pydantic import BaseModel


class LLMResponse(BaseModel):
    text: str
    error: str | None = None


class LLMProvider(Protocol):
    def complete(self, prompt: str) -> LLMResponse:
        """Return model text for a prompt."""


class MockLLMProvider:
    """Deterministic provider used in tests and default CLI flows."""

    def __init__(self, response_text: str | None = None) -> None:
        self.response_text = response_text or "[]"
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> LLMResponse:
        self.prompts.append(prompt)
        return LLMResponse(text=self.response_text)


class OpenAICompatibleProvider:
    """Minimal OpenAI-compatible chat completions client."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("LOOPOS_LLM_BASE_URL") or "https://api.openai.com").rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("LOOPOS_LLM_API_KEY")
        self.model = model or os.getenv("LOOPOS_LLM_MODEL") or "gpt-4.1-mini"
        raw_timeout = timeout_seconds or int(os.getenv("LOOPOS_LLM_TIMEOUT_SECONDS", "30"))
        self.timeout_seconds = max(raw_timeout, 1)

    def complete(self, prompt: str) -> LLMResponse:
        if not self.api_key:
            return LLMResponse(
                text="",
                error="LOOPOS_LLM_API_KEY is not configured; no network request was made.",
            )
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Return strict JSON only. Do not include markdown.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return LLMResponse(text="", error=f"LLM request failed: {exc}")

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            return LLMResponse(text="", error=f"LLM response shape is invalid: {exc}")
        return LLMResponse(text=str(content))
