"""Tests for OpenAI-compatible provider boundary."""

import pytest

from loopos.model_kernel.openai_compatible import (
    OpenAICompatibleClient,
    OpenAICompatibleConfig,
    ProviderResponseError,
)


def test_config_available_with_key() -> None:
    cfg = OpenAICompatibleConfig(api_key="sk-test-123")
    assert cfg.is_available


def test_config_unavailable_without_key() -> None:
    cfg = OpenAICompatibleConfig()
    assert not cfg.is_available


def test_config_unavailable_empty_key() -> None:
    cfg = OpenAICompatibleConfig(api_key="   ")
    assert not cfg.is_available


def test_build_request() -> None:
    cfg = OpenAICompatibleConfig(api_key="sk-test", model="gpt-4o")
    client = OpenAICompatibleClient(cfg)
    request = client.build_request(
        [{"role": "user", "content": "Hello"}],
        temperature=0.5,
    )
    assert "url" in request
    assert request["headers"]["Authorization"] == "Bearer sk-test"
    assert request["body"]["model"] == "gpt-4o"
    assert request["body"]["messages"][0]["content"] == "Hello"


def test_build_request_unavailable() -> None:
    cfg = OpenAICompatibleConfig()
    client = OpenAICompatibleClient(cfg)
    with pytest.raises(RuntimeError, match="not available"):
        client.build_request([{"role": "user", "content": "test"}])


def test_build_request_custom_base_url() -> None:
    cfg = OpenAICompatibleConfig(
        api_key="sk-test",
        base_url="https://custom.endpoint.com/v1",
    )
    client = OpenAICompatibleClient(cfg)
    request = client.build_request([{"role": "user", "content": "hi"}])
    assert "custom.endpoint.com" in request["url"]


def test_parse_response() -> None:
    cfg = OpenAICompatibleConfig(api_key="sk-test")
    client = OpenAICompatibleClient(cfg)
    raw = {
        "id": "chatcmpl-abc",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "gpt-4",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello back!"},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 5,
            "completion_tokens": 3,
            "total_tokens": 8,
        },
    }
    response = client.parse_response(raw)
    assert response.id == "chatcmpl-abc"
    assert len(response.choices) == 1
    assert response.choices[0].message.content == "Hello back!"
    assert response.usage.total_tokens == 8


def test_parse_error_response() -> None:
    cfg = OpenAICompatibleConfig(api_key="sk-test")
    client = OpenAICompatibleClient(cfg)
    raw = {
        "error": {
            "type": "invalid_request_error",
            "message": "Invalid model specified",
        }
    }
    with pytest.raises(ProviderResponseError) as exc_info:
        client.parse_response(raw)
    assert "Invalid model" in str(exc_info.value)


def test_parse_error_normalized() -> None:
    cfg = OpenAICompatibleConfig(api_key="sk-test", provider_id="custom")
    client = OpenAICompatibleClient(cfg)
    error = client.parse_error(
        {"error": {"type": "rate_limit", "message": "Too many requests"}},
        status_code=429,
    )
    assert error.status_code == 429
    assert error.provider_id == "custom"
    assert error.error_type == "rate_limit"
