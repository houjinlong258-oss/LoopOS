"""Tests for webhook gateway boundary."""

from loopos.gateway.auth import GatewayAuthPolicy
from loopos.gateway.models import GatewayChannel
from loopos.gateway.webhook import (
    WebhookApprovalHandler,
    WebhookHealthHandler,
    WebhookMessageHandler,
)


def _make_auth(*, require_token: bool = False) -> GatewayAuthPolicy:
    tokens: dict[GatewayChannel, str] = {"webhook": "secret123"} if require_token else {}
    return GatewayAuthPolicy(
        allowlists={"webhook": {"user-1", "user-2"}},
        tokens=tokens,
    )


def test_health_ok() -> None:
    handler = WebhookHealthHandler()
    resp = handler.handle()
    assert resp.status == "ok"
    assert "timestamp" in resp.data


def test_message_accepted() -> None:
    auth = _make_auth()
    handler = WebhookMessageHandler(auth)
    resp = handler.handle("user-1", "hello world")
    assert resp.status == "ok"
    assert "message_id" in resp.data
    assert len(handler.received) == 1


def test_message_unauthorized() -> None:
    auth = _make_auth()
    handler = WebhookMessageHandler(auth)
    resp = handler.handle("unknown-user", "hello")
    assert resp.status == "unauthorized"
    assert len(handler.received) == 0


def test_message_invalid_empty_text() -> None:
    auth = _make_auth()
    handler = WebhookMessageHandler(auth)
    resp = handler.handle("user-1", "")
    assert resp.status == "invalid"


def test_message_invalid_empty_user() -> None:
    auth = _make_auth()
    handler = WebhookMessageHandler(auth)
    resp = handler.handle("", "hello")
    assert resp.status == "invalid"


def test_message_token_required() -> None:
    auth = _make_auth(require_token=True)
    handler = WebhookMessageHandler(auth)

    # Without token
    resp = handler.handle("user-1", "hello")
    assert resp.status == "unauthorized"

    # With valid token
    resp = handler.handle("user-1", "hello", token="secret123")
    assert resp.status == "ok"


def test_approval_approve() -> None:
    auth = _make_auth()
    handler = WebhookApprovalHandler(auth)
    resp = handler.handle("user-1", "appr-1", "approve", run_id="run-1")
    assert resp.status == "ok"
    assert resp.data["decision"] == "approve"
    assert len(handler.decisions) == 1
    assert handler.decisions[0].approve


def test_approval_deny() -> None:
    auth = _make_auth()
    handler = WebhookApprovalHandler(auth)
    resp = handler.handle("user-1", "appr-1", "deny", run_id="run-1")
    assert resp.status == "ok"
    assert resp.data["decision"] == "deny"
    assert handler.decisions[0].deny


def test_approval_unauthorized() -> None:
    auth = _make_auth()
    handler = WebhookApprovalHandler(auth)
    resp = handler.handle("unknown", "appr-1", "approve")
    assert resp.status == "unauthorized"


def test_approval_invalid_empty_id() -> None:
    auth = _make_auth()
    handler = WebhookApprovalHandler(auth)
    resp = handler.handle("user-1", "", "approve")
    assert resp.status == "invalid"
