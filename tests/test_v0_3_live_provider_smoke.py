"""Gated live-provider smoke test for v0.3.

This test exercises the **live call** path of the v0.3 provider
runtime. It is **gated** by the ``LOOPOS_LIVE_SMOKE=1`` environment
variable: by default the test is skipped so CI never makes a
real provider call. The same proof is also available as a
standalone script at ``scripts/v0_3_live_provider_smoke.py`` for
manual runs.

To run manually::

    LOOPOS_LIVE_SMOKE=1 python -m pytest tests/test_v0_3_live_provider_smoke.py -v
    python scripts/v0_3_live_provider_smoke.py

The transport is **injected** (a Python closure that returns a
synthetic OpenAI-shape response). The test does **no** real network
I/O. The point is to prove the runtime's live-call contract
(headers, body, response parsing, secret redaction) without ever
opening a socket.
"""

from __future__ import annotations

from typing import Any

import os
import pytest

# Gate: do not run in CI by default. Set LOOPOS_LIVE_SMOKE=1 to enable.
_LIVE_SMOKE_ENABLED = os.environ.get("LOOPOS_LIVE_SMOKE") == "1"

pytestmark = pytest.mark.skipif(
    not _LIVE_SMOKE_ENABLED,
    reason="LOOPOS_LIVE_SMOKE not set; live-provider smoke is gated",
)


TEST_API_KEY = "sk-smoke-test-key-do-not-leak-12345"
TEST_BASE_URL = "https://example.invalid/v1"


@pytest.fixture
def captured() -> dict[str, Any]:
    return {}


@pytest.fixture
def transport_factory(captured: dict[str, Any]) -> Any:
    from loopos.providers_runtime.openai import (
        PreparedRequest,
        PreparedResponse,
    )

    def _factory() -> object:
        def transport(req: PreparedRequest) -> PreparedResponse:
            captured["request"] = req
            return PreparedResponse(
                status=200,
                body={
                    "id": "chatcmpl-smoke",
                    "object": "chat.completion",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": "Hello from the smoke transport.",
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 3,
                        "completion_tokens": 5,
                        "total_tokens": 8,
                    },
                },
            )

        return transport

    return _factory


def test_provider_configured_explicitly(transport_factory: Any) -> None:
    from loopos.providers_runtime import OpenAICompatibleProviderRuntime

    runtime = OpenAICompatibleProviderRuntime(
        api_key=TEST_API_KEY,
        base_url=TEST_BASE_URL,
        transport=transport_factory(),
    )
    info = runtime.info()
    assert info.configured is True
    assert info.base_url == TEST_BASE_URL


def test_dry_run_does_not_call_transport(transport_factory: Any, captured: dict[str, Any]) -> None:
    from loopos.providers_runtime import (
        ModelCallRequest,
        ModelMessage,
        OpenAICompatibleProviderRuntime,
    )

    runtime = OpenAICompatibleProviderRuntime(
        api_key=TEST_API_KEY, base_url=TEST_BASE_URL,
        transport=transport_factory(),
    )
    req = ModelCallRequest(
        provider_id="openai", model_id="gpt-4.1",
        messages=[ModelMessage(role="user", content="hi")],
        live_provider_calls_allowed=False,
    )
    resp = runtime.call(req)
    assert resp.status == "dry_run"
    assert "request" not in captured


def test_live_call_returns_real_response(transport_factory: Any) -> None:
    from loopos.providers_runtime import (
        ModelCallRequest,
        ModelMessage,
        OpenAICompatibleProviderRuntime,
    )

    runtime = OpenAICompatibleProviderRuntime(
        api_key=TEST_API_KEY, base_url=TEST_BASE_URL,
        transport=transport_factory(),
    )
    req = ModelCallRequest(
        provider_id="openai", model_id="gpt-4.1",
        messages=[ModelMessage(role="user", content="hi")],
        live_provider_calls_allowed=True,
    )
    resp = runtime.call(req)
    assert resp.status == "completed"
    assert "Hello from the smoke transport" in (resp.content or "")
    assert resp.usage is not None
    assert resp.usage.total_tokens == 8


def test_request_shape(transport_factory: Any, captured: dict[str, Any]) -> None:
    from loopos.providers_runtime import (
        ModelCallRequest,
        ModelMessage,
        OpenAICompatibleProviderRuntime,
    )

    runtime = OpenAICompatibleProviderRuntime(
        api_key=TEST_API_KEY, base_url=TEST_BASE_URL,
        transport=transport_factory(),
    )
    req = ModelCallRequest(
        provider_id="openai", model_id="gpt-4.1",
        messages=[ModelMessage(role="user", content="hi")],
        live_provider_calls_allowed=True,
    )
    runtime.call(req)
    wire = captured["request"]
    assert wire.method == "POST"
    assert wire.url.endswith("/chat/completions")
    assert wire.headers.get("Content-Type") == "application/json"
    assert wire.body.get("model") == "gpt-4.1"
    assert isinstance(wire.body.get("messages"), list)


def test_transport_sees_real_key(transport_factory: Any, captured: dict[str, Any]) -> None:
    """The wire call must carry the real key (otherwise the provider
    would reject it), but the runtime's stored ``last_prepared``
    must not."""
    from loopos.providers_runtime import (
        ModelCallRequest,
        ModelMessage,
        OpenAICompatibleProviderRuntime,
    )

    runtime = OpenAICompatibleProviderRuntime(
        api_key=TEST_API_KEY, base_url=TEST_BASE_URL,
        transport=transport_factory(),
    )
    req = ModelCallRequest(
        provider_id="openai", model_id="gpt-4.1",
        messages=[ModelMessage(role="user", content="hi")],
        live_provider_calls_allowed=True,
    )
    runtime.call(req)
    auth = captured["request"].headers.get("Authorization", "")
    assert auth.startswith("Bearer ")
    assert TEST_API_KEY in auth


def test_last_prepared_redacts_key(transport_factory: Any) -> None:
    from loopos.providers_runtime import (
        ModelCallRequest,
        ModelMessage,
        OpenAICompatibleProviderRuntime,
    )

    runtime = OpenAICompatibleProviderRuntime(
        api_key=TEST_API_KEY, base_url=TEST_BASE_URL,
        transport=transport_factory(),
    )
    req = ModelCallRequest(
        provider_id="openai", model_id="gpt-4.1",
        messages=[ModelMessage(role="user", content="hi")],
        live_provider_calls_allowed=True,
    )
    runtime.call(req)
    assert runtime.last_prepared is not None
    last_auth = runtime.last_prepared.headers.get("Authorization", "")
    assert last_auth == "Bearer ***REDACTED***"
    assert TEST_API_KEY not in last_auth
    assert TEST_API_KEY not in runtime.last_prepared.model_dump_json()


def test_missing_key_returns_blocked() -> None:
    from loopos.providers_runtime import (
        ModelCallRequest,
        ModelMessage,
        OpenAICompatibleProviderRuntime,
    )
    import os

    os.environ.pop("OPENAI_API_KEY", None)
    no_key = OpenAICompatibleProviderRuntime(
        base_url=TEST_BASE_URL,
        transport=lambda req: (_ for _ in ()).throw(
            AssertionError("transport should not be called without a key")
        ),
    )
    req = ModelCallRequest(
        provider_id="openai", model_id="gpt-4.1",
        messages=[ModelMessage(role="user", content="hi")],
        live_provider_calls_allowed=True,
    )
    resp = no_key.call(req)
    assert resp.status == "blocked"
    assert "provider_config_missing" in (resp.reason_codes or [])


def test_budget_guard_blocks_over_limit() -> None:
    from loopos.providers_runtime import ProviderBudget

    budget = ProviderBudget(max_usd=0.001, used_usd=0.0)
    decision = budget.check(1.0, approved=True)
    assert not decision.allowed
    assert "provider_budget_exceeded" in decision.reason_codes


def test_secret_redaction_strips_api_keys() -> None:
    from loopos.providers_runtime import redact_secrets

    raw = "leak: sk-leaktest-1234567890 with Bearer sk-leaktest-1234567890"
    redacted = redact_secrets(raw)
    assert "sk-leaktest" not in redacted
    assert "REDACTED" in redacted
    assert TEST_API_KEY not in redact_secrets(f"k={TEST_API_KEY}")
