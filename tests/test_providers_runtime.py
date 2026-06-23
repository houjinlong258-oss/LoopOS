"""Tests for ``loopos.providers_runtime``."""

from __future__ import annotations

import os


from loopos.providers_runtime import (
    ModelCallRequest,
    ModelMessage,
    MockProviderRuntime,
    OpenAICompatibleProviderRuntime,
    OllamaProviderRuntime,
    ProviderBudget,
    ProviderRuntimeRegistry,
    redact_secrets,
)
from loopos.providers_runtime.openai import PreparedRequest, PreparedResponse


def test_mock_provider_runtime_returns_completed() -> None:
    rt = MockProviderRuntime()
    req = ModelCallRequest(
        provider_id="mock",
        model_id="m",
        messages=[ModelMessage(role="user", content="hi")],
    )
    resp = rt.call(req)
    assert resp.status == "completed"
    assert "hi" in (resp.content or "")


def test_mock_provider_runtime_marks_live_disabled() -> None:
    rt = MockProviderRuntime()
    req = ModelCallRequest(
        provider_id="mock",
        model_id="m",
        messages=[ModelMessage(role="user", content="hi")],
        live_provider_calls_allowed=False,
    )
    resp = rt.call(req)
    assert "live_provider_disabled" in resp.reason_codes


def test_openai_blocked_by_default() -> None:
    os.environ.pop("OPENAI_API_KEY", None)
    rt = OpenAICompatibleProviderRuntime()
    req = ModelCallRequest(
        provider_id="openai",
        model_id="gpt-4.1",
        messages=[ModelMessage(role="user", content="hi")],
    )
    resp = rt.call(req)
    assert resp.status == "dry_run"
    assert "dry_run" in resp.reason_codes


def test_openai_uses_injected_transport() -> None:
    # Set a key so live calls succeed; the transport is the only thing
    # that actually gets called.
    os.environ["OPENAI_API_KEY"] = "sk-test-transport-key-12345"
    try:
        def fake_transport(req: PreparedRequest) -> PreparedResponse:
            return PreparedResponse(
                status=200,
                body={
                    "choices": [
                        {"message": {"role": "assistant", "content": "echoed"}}
                    ],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                },
            )

        rt = OpenAICompatibleProviderRuntime(transport=fake_transport)
        req = ModelCallRequest(
            provider_id="openai",
            model_id="gpt-4.1",
            messages=[ModelMessage(role="user", content="hi")],
            live_provider_calls_allowed=True,
        )
        resp = rt.call(req)
        assert resp.status == "completed"
        assert resp.content == "echoed"
        assert rt.last_prepared is not None
        # SECURITY: last_prepared is a Pydantic model that callers may
        # serialise and log. The Authorization header must be redacted
        # so the real key is never leaked through that field. The
        # transport itself receives the un-redacted key in its request
        # argument (which is local to this call and not stored).
        auth = rt.last_prepared.headers["Authorization"]
        assert auth == "Bearer ***REDACTED***"
        assert "sk-test-transport-key-12345" not in auth
    finally:
        os.environ.pop("OPENAI_API_KEY", None)


def test_ollama_dry_run_when_not_live() -> None:
    os.environ.pop("OLLAMA_HOST", None)
    rt = OllamaProviderRuntime()
    req = ModelCallRequest(
        provider_id="ollama",
        model_id="llama3",
        messages=[ModelMessage(role="user", content="hi")],
    )
    resp = rt.call(req)
    assert resp.status == "dry_run"


def test_ollama_uses_injected_transport() -> None:
    def fake(req: PreparedRequest) -> PreparedResponse:
        return PreparedResponse(
            status=200,
            body={
                "message": {"role": "assistant", "content": "hi back"},
                "prompt_eval_count": 3,
                "eval_count": 2,
            },
        )

    rt = OllamaProviderRuntime(transport=fake)
    req = ModelCallRequest(
        provider_id="ollama",
        model_id="llama3",
        messages=[ModelMessage(role="user", content="hi")],
        live_provider_calls_allowed=True,
    )
    resp = rt.call(req)
    assert resp.status == "completed"
    assert resp.content == "hi back"


def test_budget_blocks_over_max() -> None:
    b = ProviderBudget(max_usd=0.10)
    d = b.check(0.50)
    assert not d.allowed
    assert "provider_budget_exceeded" in d.reason_codes


def test_budget_allows_under_max() -> None:
    b = ProviderBudget(max_usd=1.0)
    d = b.check(0.10)
    assert d.allowed


def test_budget_requires_approval_above_threshold() -> None:
    b = ProviderBudget(max_usd=10.0, require_approval_above_usd=1.0)
    d = b.check(2.0, approved=False)
    assert d.requires_approval
    assert "provider_call_requires_approval" in d.reason_codes


def test_redact_secrets_masks_env_key() -> None:
    os.environ["OPENAI_API_KEY"] = "sk-supersecret1234567890"
    try:
        text = "Authorization: Bearer sk-supersecret1234567890"
        out = redact_secrets(text)
        assert "sk-supersecret" not in out
        assert "REDACTED" in out
    finally:
        os.environ.pop("OPENAI_API_KEY", None)


def test_redact_secrets_handles_no_keys() -> None:
    assert redact_secrets("plain text") == "plain text"
    assert redact_secrets("") == ""


def test_redact_secrets_preserves_normal_text() -> None:
    text = "normal text with no secrets"
    assert redact_secrets(text) == text


def test_provider_runtime_registry_has_defaults() -> None:
    reg = ProviderRuntimeRegistry()
    ids = sorted(r.provider_id for r in reg.list_runtimes())
    assert "mock" in ids
    assert "openai" in ids
    assert "ollama" in ids


def test_provider_runtime_registry_inspect() -> None:
    reg = ProviderRuntimeRegistry()
    info = reg.inspect("mock")
    assert info is not None
    assert info["provider_id"] == "mock"


def test_provider_runtime_registry_duplicate_register() -> None:
    reg = ProviderRuntimeRegistry(register_defaults=False)
    reg.register(MockProviderRuntime())
    reg.register(MockProviderRuntime())  # should be a no-op
    assert len(reg.list_runtimes()) == 1
