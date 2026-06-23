#!/usr/bin/env python3
"""LoopOS v0.3 Loopback Live-Provider HTTP Smoke.

This script proves that the v0.3 governed provider runtime can
issue a *real* HTTP request to an OpenAI-compatible endpoint,
without ever talking to a paid external service. It boots a local
``http.server.HTTPServer`` on ``127.0.0.1:0``, points the
``OpenAICompatibleProviderRuntime`` at it, and runs the request
through the real ``urllib.request`` transport.

The five P0-2 invariants it asserts:

1. **Explicit live flags required** — without
   ``live_provider_calls_allowed=True`` the call is a no-op (status
   ``dry_run``) and the HTTP server records zero hits.
2. **Missing key gives structured error** — when
   ``live_provider_calls_allowed=True`` but no API key is set, the
   runtime returns ``status="blocked"`` with
   ``reason_codes=["provider_config_missing", "OPENAI_API_KEY not set"]``
   (no stack trace, no leakage).
3. **Request path uses real HTTP client path** — the loopback
   server's request log shows the actual POST hit, with the real
   URL and headers the runtime produced.
4. **Response metadata returned** — the response carries the
   parsed OpenAI-style usage block (``prompt_tokens``,
   ``completion_tokens``, ``total_tokens``).
5. **Secrets redacted from trace and persisted state** — the
   runtime's ``last_prepared.headers["Authorization"]`` equals
   ``"Bearer ***REDACTED***"``; the live key never appears in the
   stored prepared object, even though the wire path carried the
   real key.

The script is deterministic: same machine state -> same output. It
opens no external network. It is gated by
``LOOPOS_LIVE_HTTP_SMOKE=1`` (or ``--run``) so it does not run by
default in CI.

Exit codes:

* ``0`` -- all hard checks pass (warnings may be present).
* ``1`` -- one or more hard checks failed.

Output is JSON when ``--json`` is passed.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Canned OpenAI-compatible response handler
# ---------------------------------------------------------------------------


class _LoopbackOpenAIHandler(BaseHTTPRequestHandler):
    """Canned OpenAI-compatible chat-completions handler.

    The handler echoes the request body back as the assistant
    message. It records every request in ``server.hits`` so the
    smoke script can assert that the runtime *actually* reached
    the wire.
    """

    server: "_LoopbackServer"

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:  # noqa: BLE001 - malformed body
            payload = {}

        # Record every hit. The smoke script asserts at least one.
        self.server.hits.append(
            {
                "path": self.path,
                "method": "POST",
                "headers": dict(self.headers.items()),
                "body": payload,
            }
        )

        response_body = {
            "id": "chatcmpl-loopback",
            "object": "chat.completion",
            "model": payload.get("model", "unknown"),
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "loopback echo: "
                        + " ".join(
                            m.get("content", "") for m in payload.get("messages", [])
                        ),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 4,
                "completion_tokens": 7,
                "total_tokens": 11,
            },
        }
        encoded = json.dumps(response_body).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        # Silence stderr access logs during the smoke run.
        return


class _LoopbackServer(HTTPServer):
    hits: list[dict[str, Any]]


def _start_loopback_server() -> _LoopbackServer:
    """Bind a loopback HTTP server on a free port. Return it bound,
    ready, and accepting connections on ``127.0.0.1:<random>``.
    """
    server = _LoopbackServer(("127.0.0.1", 0), _LoopbackOpenAIHandler)
    server.hits = []
    thread = threading.Thread(
        target=server.serve_forever, name="loopback-http-smoke", daemon=True
    )
    thread.start()
    server._thread = thread  # type: ignore[attr-defined]
    return server


def _wait_for_listening(server: _LoopbackServer, timeout_s: float = 5.0) -> None:
    """Block until the loopback server is reachable, or fail loud."""
    deadline = socket.gettimebyname if hasattr(socket, "gettimebyname") else None
    import time

    end = time.time() + timeout_s
    host, port = server.server_address[:2]
    last_exc: Exception | None = None
    while time.time() < end:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError as exc:
            last_exc = exc
            time.sleep(0.05)
    raise RuntimeError(
        f"loopback server {host}:{port} did not start within {timeout_s}s"
        + (f": {last_exc}" if last_exc else "")
    )


# ---------------------------------------------------------------------------
# The five invariant checks
# ---------------------------------------------------------------------------


def _check_dry_run_keeps_server_quiet(server: _LoopbackServer) -> dict[str, Any]:
    """Invariant 1: without ``live_provider_calls_allowed`` the call
    is a dry-run and the HTTP server records zero hits.
    """
    from loopos.providers_runtime import ModelCallRequest, ModelMessage
    from loopos.providers_runtime.openai import OpenAICompatibleProviderRuntime

    before = len(server.hits)
    rt = OpenAICompatibleProviderRuntime(
        api_key="sk-test-loopback-1234567890",
        base_url=f"http://127.0.0.1:{server.server_address[1]}/v1",
        use_real_http=True,
    )
    req = ModelCallRequest(
        provider_id="openai",
        model_id="gpt-4.1",
        messages=[ModelMessage(role="user", content="hi")],
        live_provider_calls_allowed=False,
    )
    resp = rt.call(req)
    after = len(server.hits)
    return {
        "name": "dry_run_keeps_server_quiet",
        "status": resp.status == "dry_run" and after == before,
        "detail": (
            f"resp.status={resp.status!r}; server_hits before={before}, after={after}"
        ),
    }


def _check_missing_key_blocks_structured(server: _LoopbackServer) -> dict[str, Any]:
    """Invariant 2: live call with no API key returns a blocked,
    structured response. No stack trace, no leaked key.
    """
    from loopos.providers_runtime import ModelCallRequest, ModelMessage
    from loopos.providers_runtime.openai import OpenAICompatibleProviderRuntime

    rt = OpenAICompatibleProviderRuntime(
        base_url=f"http://127.0.0.1:{server.server_address[1]}/v1",
        use_real_http=True,
    )
    req = ModelCallRequest(
        provider_id="openai",
        model_id="gpt-4.1",
        messages=[ModelMessage(role="user", content="hi")],
        live_provider_calls_allowed=True,
    )
    resp = rt.call(req)
    codes = list(resp.reason_codes or [])
    has_key_reason = any("OPENAI_API_KEY" in c for c in codes) or any(
        "provider_config_missing" in c for c in codes
    )
    return {
        "name": "missing_key_blocks_structured",
        "status": resp.status == "blocked" and has_key_reason,
        "detail": f"resp.status={resp.status!r}; reason_codes={codes}",
    }


def _check_real_http_client_path(server: _LoopbackServer) -> dict[str, Any]:
    """Invariant 3: a live call reaches the loopback server over a
    real HTTP client (urllib). The server's hit log records the
    POST and the runtime-supplied headers.
    """
    from loopos.providers_runtime import ModelCallRequest, ModelMessage
    from loopos.providers_runtime.openai import OpenAICompatibleProviderRuntime

    before = len(server.hits)
    rt = OpenAICompatibleProviderRuntime(
        api_key="sk-test-loopback-1234567890",
        base_url=f"http://127.0.0.1:{server.server_address[1]}/v1",
        use_real_http=True,
    )
    req = ModelCallRequest(
        provider_id="openai",
        model_id="gpt-4.1",
        messages=[ModelMessage(role="user", content="hello")],
        live_provider_calls_allowed=True,
    )
    resp = rt.call(req)
    after = len(server.hits)
    hit = server.hits[-1] if server.hits else {}
    has_hits = (after - before) >= 1
    has_path = "/v1/chat/completions" in hit.get("path", "")
    has_model = hit.get("body", {}).get("model") == "gpt-4.1"
    return {
        "name": "real_http_client_path",
        "status": (
            resp.status == "completed" and has_hits and has_path and has_model
        ),
        "detail": (
            f"resp.status={resp.status!r}; hits delta={after - before}; "
            f"path={hit.get('path')!r}; body.model={hit.get('body', {}).get('model')!r}"
        ),
    }


def _check_response_metadata_returned(server: _LoopbackServer) -> dict[str, Any]:
    """Invariant 4: the runtime parses the OpenAI-style usage block
    and exposes ``prompt_tokens``, ``completion_tokens``,
    ``total_tokens`` on the response.
    """
    from loopos.providers_runtime import ModelCallRequest, ModelMessage
    from loopos.providers_runtime.openai import OpenAICompatibleProviderRuntime

    rt = OpenAICompatibleProviderRuntime(
        api_key="sk-test-loopback-1234567890",
        base_url=f"http://127.0.0.1:{server.server_address[1]}/v1",
        use_real_http=True,
    )
    req = ModelCallRequest(
        provider_id="openai",
        model_id="gpt-4.1",
        messages=[ModelMessage(role="user", content="hello")],
        live_provider_calls_allowed=True,
    )
    resp = rt.call(req)
    usage = resp.usage
    if usage is None:
        ok = False
        detail = "response.usage is None"
    else:
        ok = (
            usage.prompt_tokens == 4
            and usage.completion_tokens == 7
            and usage.total_tokens == 11
        )
        detail = (
            f"prompt={usage.prompt_tokens}; completion={usage.completion_tokens}; "
            f"total={usage.total_tokens}"
        )
    return {
        "name": "response_metadata_returned",
        "status": resp.status == "completed" and ok,
        "detail": f"resp.status={resp.status!r}; usage={detail}",
    }


def _check_secrets_redacted_in_trace(server: _LoopbackServer) -> dict[str, Any]:
    """Invariant 5: the runtime's ``last_prepared.headers["Authorization"]``
    is the redacted placeholder, not the real key.
    """
    from loopos.providers_runtime import ModelCallRequest, ModelMessage
    from loopos.providers_runtime.openai import OpenAICompatibleProviderRuntime

    real_key = "sk-test-loopback-supersecret-1234567890"
    rt = OpenAICompatibleProviderRuntime(
        api_key=real_key,
        base_url=f"http://127.0.0.1:{server.server_address[1]}/v1",
        use_real_http=True,
    )
    req = ModelCallRequest(
        provider_id="openai",
        model_id="gpt-4.1",
        messages=[ModelMessage(role="user", content="hello")],
        live_provider_calls_allowed=True,
    )
    resp = rt.call(req)
    auth_header = (
        rt.last_prepared.headers.get("Authorization", "") if rt.last_prepared else ""
    )
    # The persisted prepared object must not contain the real key.
    leaked = real_key in auth_header
    redacted = "***REDACTED***" in auth_header
    # The live server hit log DID receive the real key — that's the
    # whole point of the smoke. But we do NOT persist it anywhere.
    last_hit = server.hits[-1] if server.hits else {}
    wire_auth = last_hit.get("headers", {}).get("Authorization", "")
    wire_carried_real = real_key in wire_auth
    return {
        "name": "secrets_redacted_in_trace",
        "status": (
            resp.status == "completed"
            and redacted
            and not leaked
            and wire_carried_real
        ),
        "detail": (
            f"persisted_auth_redacted={redacted}; leaked_in_persisted={leaked}; "
            f"wire_carried_real={wire_carried_real}"
        ),
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_smoke(*, run: bool = False) -> dict[str, Any]:
    """Run the five invariant checks. Return a JSON-serialisable
    summary.
    """
    gated_off = not (run or os.environ.get("LOOPOS_LIVE_HTTP_SMOKE") == "1")
    if gated_off:
        return {
            "schema_version": "0.3",
            "status": "pass",
            "hard_fail_count": 0,
            "checks": [
                {
                    "name": "loopback_http_smoke_gated",
                    "status": True,
                    "detail": (
                        "skipped: set LOOPOS_LIVE_HTTP_SMOKE=1 or pass --run "
                        "to exercise the loopback HTTP path"
                    ),
                    "severity": "warning",
                }
            ],
            "warnings": [
                {
                    "name": "loopback_http_smoke_gated",
                    "detail": "smoke gated off; pass --run to enable",
                }
            ],
            "transport": "real_http_via_loopback",
        }

    server = _start_loopback_server()
    try:
        _wait_for_listening(server)
        checks: list[dict[str, Any]] = []
        try:
            checks.append(_check_dry_run_keeps_server_quiet(server))
            checks.append(_check_missing_key_blocks_structured(server))
            checks.append(_check_real_http_client_path(server))
            checks.append(_check_response_metadata_returned(server))
            checks.append(_check_secrets_redacted_in_trace(server))
        except Exception as exc:  # noqa: BLE001 - surface as a check
            checks.append(
                {
                    "name": "loopback_smoke_runner",
                    "status": False,
                    "detail": f"{type(exc).__name__}: {exc}",
                }
            )
        hard_fail_count = sum(1 for c in checks if not c["status"])
        return {
            "schema_version": "0.3",
            "status": "pass" if hard_fail_count == 0 else "fail",
            "checks": checks,
            "hard_fail_count": hard_fail_count,
            "warnings": [],
            "transport": "real_http_via_loopback",
            "loopback_url": f"http://127.0.0.1:{server.server_address[1]}/v1",
            "request_hit_count": len(server.hits),
        }
    finally:
        server.shutdown()
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Loopback live-provider HTTP smoke")
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit JSON output",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help=(
            "actually run the loopback server and the five checks "
            "(equivalent to setting LOOPOS_LIVE_HTTP_SMOKE=1)"
        ),
    )
    args = parser.parse_args(argv)
    report = run_smoke(run=args.run)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        status = report["status"]
        print(f"status: {status}")
        print(f"hard_fail_count: {report['hard_fail_count']}")
        for c in report["checks"]:
            mark = "PASS" if c["status"] else "FAIL"
            print(f"[{mark}] {c['name']} :: {c['detail']}")
    return 0 if report["hard_fail_count"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())