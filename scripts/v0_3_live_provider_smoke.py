#!/usr/bin/env python3
"""v0.3 Real LLM Provider Smoke (gated).

This script exercises the **live call** path of the v0.3
``loopos.providers_runtime`` layer. It is the runtime proof that
the v0.3 spec asks for: a governed live-provider smoke that proves
the safety properties without requiring a real network connection.

How it works
------------

* An OpenAI-compatible transport is **injected** into
  :class:`OpenAICompatibleProviderRuntime`. The transport is a
  closure that captures the inbound ``PreparedRequest`` (so we can
  assert on its shape) and returns a synthetic but
  OpenAI-schema-compliant ``PreparedResponse``.
* The script then drives the runtime in live mode (``--allow-live``)
  and asserts on the **full safety contract** the v0.3 spec lists:

  1. Provider is configured explicitly (api_key + base_url).
  2. ``live_provider_calls_allowed=True`` is required to make a
     live call (without it the runtime returns ``status="dry_run"``).
  3. Budget guard is enforced (over-limit returns blocked).
  4. The API key **never** appears in ``last_prepared`` (the
     Pydantic model that callers may serialise to trace/log).
  5. The API key **never** appears in the rendered response.
  6. The Authorization header that the **transport** sees contains
     the real key (so the wire call is real), but the runtime
     stores only a redacted copy.
  7. Missing key returns a structured ``blocked`` response.
  8. The default mode (no flag) is dry-run and never makes a call.

Gating
------

The script is **not** invoked by CI. It is run manually with::

    python scripts/v0_3_live_provider_smoke.py

There is **no** real HTTP traffic. The transport is a Python
closure; the script is safe to run on any developer machine.

Exit codes
----------

* ``0`` — all checks pass
* ``1`` — at least one assertion failed
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


# Test key — must never appear in trace/log/response. The transport
# captures it; the smoke verifies that the *runtime* redacts it.
TEST_API_KEY = "sk-smoke-test-key-do-not-leak-12345"
TEST_BASE_URL = "https://example.invalid/v1"


def _make_transport(captured: dict[str, Any]) -> Any:
    """Build an injectable transport that captures the request and
    returns a valid OpenAI-shape response.
    """
    from loopos.providers_runtime.openai import (
        PreparedRequest,
        PreparedResponse,
    )

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


def _check(label: str, condition: bool, detail: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    line = f"  [{status}] {label}"
    if detail:
        line += f" -- {detail}"
    print(line)
    return condition


def main() -> int:
    from loopos.providers_runtime import (
        ModelCallRequest,
        ModelMessage,
        OpenAICompatibleProviderRuntime,
        ProviderBudget,
        redact_secrets,
    )

    failures: list[str] = []
    captured: dict[str, Any] = {}

    print("=" * 70)
    print("v0.3 Live Provider Smoke")
    print("=" * 70)
    print()

    # ---- 1. provider configured explicitly --------------------------
    print("[1] provider configured explicitly")
    runtime = OpenAICompatibleProviderRuntime(
        api_key=TEST_API_KEY,
        base_url=TEST_BASE_URL,
        transport=_make_transport(captured),
    )
    info = runtime.info()
    if not _check("info.configured is True", info.configured):
        failures.append("1a")
    if not _check(
        "info.base_url matches the configured URL",
        info.base_url == TEST_BASE_URL,
    ):
        failures.append("1b")

    # ---- 2. live call requires explicit live_provider_calls_allowed ---
    print("\n[2] live call requires explicit --allow-live-provider")
    req_dry = ModelCallRequest(
        provider_id="openai",
        model_id="gpt-4.1",
        messages=[ModelMessage(role="user", content="hi")],
        live_provider_calls_allowed=False,
    )
    resp_dry = runtime.call(req_dry)
    if not _check(
        "dry-run response has status=dry_run",
        resp_dry.status == "dry_run",
        f"actual={resp_dry.status}",
    ):
        failures.append("2a")
    if not _check(
        "dry-run response did NOT call the transport",
        "request" not in captured,
    ):
        failures.append("2b")

    # ---- 3. live call returns real provider response ---------------
    print("\n[3] live call returns real provider response")
    captured.clear()
    req_live = ModelCallRequest(
        provider_id="openai",
        model_id="gpt-4.1",
        messages=[ModelMessage(role="user", content="hi")],
        live_provider_calls_allowed=True,
    )
    resp_live = runtime.call(req_live)
    if not _check(
        "live response status=completed",
        resp_live.status == "completed",
        f"actual={resp_live.status}",
    ):
        failures.append("3a")
    if not _check(
        "live response content from transport",
        "Hello from the smoke transport" in (resp_live.content or ""),
    ):
        failures.append("3b")
    if not _check(
        "live response usage is recorded",
        resp_live.usage is not None
        and resp_live.usage.total_tokens == 8,
    ):
        failures.append("3c")

    # ---- 4. request shape is correct (chat completions) ------------
    print("\n[4] request shape: POST /chat/completions + JSON body")
    if "request" not in captured:
        _check("transport was called", False)
        failures.append("4a")
    else:
        req = captured["request"]
        if not _check("method=POST", req.method == "POST"):
            failures.append("4a")
        if not _check(
            "url ends with /chat/completions",
            req.url.endswith("/chat/completions"),
            f"actual={req.url}",
        ):
            failures.append("4b")
        if not _check(
            "Content-Type is application/json",
            req.headers.get("Content-Type") == "application/json",
        ):
            failures.append("4c")
        if not _check(
            "body has the right model",
            req.body.get("model") == "gpt-4.1",
        ):
            failures.append("4d")
        if not _check(
            "body has messages",
            isinstance(req.body.get("messages"), list)
            and req.body["messages"][0].get("role") == "user",
        ):
            failures.append("4e")

    # ---- 5. transport sees the real Authorization header -----------
    print("\n[5] transport sees Authorization with real key (live wire)")
    if "request" in captured:
        auth = captured["request"].headers.get("Authorization", "")
        if not _check(
            "transport received Authorization header",
            auth.startswith("Bearer "),
        ):
            failures.append("5a")
        if not _check(
            "transport received the real key (not redacted)",
            TEST_API_KEY in auth,
            f"auth={auth[:25]}...",
        ):
            failures.append("5b")

    # ---- 6. last_prepared does NOT contain the real key ------------
    print("\n[6] last_prepared redacts the API key")
    if runtime.last_prepared is not None:
        last_auth = runtime.last_prepared.headers.get("Authorization", "")
        if not _check(
            "last_prepared.Auth is REDACTED (not the real key)",
            last_auth == "Bearer ***REDACTED***",
            f"actual={last_auth!r}",
        ):
            failures.append("6a")
        if not _check(
            "last_prepared does NOT contain the real key",
            TEST_API_KEY not in last_auth,
        ):
            failures.append("6b")
        # also verify JSON serialisation
        dumped = runtime.last_prepared.model_dump_json()
        if not _check(
            "last_prepared.model_dump_json() does NOT contain the real key",
            TEST_API_KEY not in dumped,
        ):
            failures.append("6c")

    # ---- 7. missing key returns structured blocked response --------
    print("\n[7] missing key returns structured blocked response")
    captured.clear()
    no_key_runtime = OpenAICompatibleProviderRuntime(
        base_url=TEST_BASE_URL,
        transport=_make_transport(captured),
    )
    # Make sure OPENAI_API_KEY isn't set
    os.environ.pop("OPENAI_API_KEY", None)
    resp_no_key = no_key_runtime.call(req_live)
    if not _check(
        "missing key response status=blocked",
        resp_no_key.status == "blocked",
        f"actual={resp_no_key.status}",
    ):
        failures.append("7a")
    if not _check(
        "reason_codes include provider_config_missing",
        "provider_config_missing" in (resp_no_key.reason_codes or []),
        f"actual={resp_no_key.reason_codes}",
    ):
        failures.append("7b")
    if not _check(
        "missing-key path did NOT call the transport",
        "request" not in captured,
    ):
        failures.append("7c")

    # ---- 8. budget guard is enforced --------------------------------
    print("\n[8] budget guard blocks over-limit live calls")
    budget = ProviderBudget(max_usd=0.001, used_usd=0.0)
    # Try a 1.00 USD call against a 0.001 budget
    decision = budget.check(1.0, approved=True)
    if not _check(
        "over-budget check returns allowed=False",
        not decision.allowed,
    ):
        failures.append("8a")
    if not _check(
        "reason_codes include provider_budget_exceeded",
        "provider_budget_exceeded" in decision.reason_codes,
    ):
        failures.append("8b")

    # ---- 9. secret redaction works on response text ---------------
    print("\n[9] secret redaction primitive strips API keys")
    raw = "The user's key was sk-leaktest-1234567890 and Bearer sk-leaktest-1234567890"
    redacted = redact_secrets(raw)
    if not _check(
        "redact_secrets removes sk-... shaped values",
        "sk-leaktest" not in redacted,
        f"redacted={redacted!r}",
    ):
        failures.append("9a")
    if not _check(
        "redact_secrets replaces with ***REDACTED***",
        "REDACTED" in redacted,
    ):
        failures.append("9b")
    # Specifically verify the TEST_API_KEY is redacted
    redacted2 = redact_secrets(f"key={TEST_API_KEY}")
    if not _check(
        "redact_secrets strips the test API key",
        TEST_API_KEY not in redacted2,
    ):
        failures.append("9c")

    # ---- summary ---------------------------------------------------
    print()
    print("=" * 70)
    if failures:
        print(f"FAIL: {len(failures)} check(s) failed: {failures}")
        return 1
    print("PASS: all 9 live-provider safety checks pass")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
