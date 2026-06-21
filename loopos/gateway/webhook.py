"""Webhook gateway boundary — local handler functions for message and approval payloads.

This module provides handler functions that simulate webhook endpoints
without requiring a production web server. All operations go through
the existing GatewayAuthPolicy and are logged to the trace store.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from loopos.gateway.auth import GatewayAuthPolicy
from loopos.gateway.models import ApprovalResumeDecision, MessageEvent


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WebhookResponse(BaseModel):
    """Standardized response from webhook handlers."""
    status: Literal["ok", "error", "unauthorized", "invalid"]
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)


class WebhookMessageHandler:
    """Handle incoming webhook messages."""

    def __init__(self, auth: GatewayAuthPolicy) -> None:
        self.auth = auth
        self.received: list[MessageEvent] = []

    def handle(
        self,
        user_id: str,
        text: str,
        *,
        token: str | None = None,
        thread_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WebhookResponse:
        """Process an incoming message payload."""
        # Validate input
        if not user_id or not user_id.strip():
            return WebhookResponse(status="invalid", message="user_id is required")
        if not text or not text.strip():
            return WebhookResponse(status="invalid", message="text is required")

        # Auth check
        auth_result = self.auth.authorize("webhook", user_id, token=token)
        if not auth_result.allowed:
            return WebhookResponse(
                status="unauthorized",
                message=auth_result.reason_code,
            )

        # Create message event
        event = MessageEvent(
            channel="webhook",
            user_id=user_id,
            text=text,
            thread_id=thread_id,
            metadata=metadata or {},
            authenticated=True,
        )
        self.received.append(event)

        return WebhookResponse(
            status="ok",
            message="message accepted",
            data={"message_id": event.id},
        )


class WebhookApprovalHandler:
    """Handle approval/denial payloads for waiting runs."""

    def __init__(self, auth: GatewayAuthPolicy) -> None:
        self.auth = auth
        self.decisions: list[ApprovalResumeDecision] = []

    def handle(
        self,
        user_id: str,
        approval_id: str,
        decision: Literal["approve", "deny"],
        *,
        token: str | None = None,
        run_id: str = "",
    ) -> WebhookResponse:
        """Process an approval or denial payload."""
        # Validate input
        if not approval_id or not approval_id.strip():
            return WebhookResponse(status="invalid", message="approval_id is required")
        if decision not in ("approve", "deny"):
            return WebhookResponse(status="invalid", message="decision must be approve or deny")

        # Auth check
        auth_result = self.auth.authorize("webhook", user_id, token=token)
        if not auth_result.allowed:
            return WebhookResponse(
                status="unauthorized",
                message=auth_result.reason_code,
            )

        # Create decision record
        resume = ApprovalResumeDecision(
            card_id=approval_id,
            run_id=run_id,
            approve=decision == "approve",
            deny=decision == "deny",
            status="approved" if decision == "approve" else "denied",
            signal=decision,
        )
        self.decisions.append(resume)

        return WebhookResponse(
            status="ok",
            message=f"approval {decision}d",
            data={
                "approval_id": approval_id,
                "decision": decision,
                "run_id": run_id,
            },
        )


class WebhookHealthHandler:
    """Simple health check endpoint."""

    def handle(self) -> WebhookResponse:
        return WebhookResponse(
            status="ok",
            message="healthy",
            data={"timestamp": _utc_now().isoformat()},
        )
