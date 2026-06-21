"""ChatOps gateway router for mock mobile/chat adapters."""

from __future__ import annotations

from loopos.gateway.adapters import MockGatewayAdapter, default_mock_adapters
from loopos.gateway.auth import GatewayAuthPolicy
from loopos.gateway.models import (
    ApprovalCard,
    ApprovalResumeDecision,
    AttachmentMetadata,
    DeliveryRecord,
    GatewayChannel,
    MessageEvent,
    utc_now,
)
from loopos.kernel.models import RunSpec


class ChatOpsGateway:
    def __init__(
        self,
        adapters: dict[GatewayChannel, MockGatewayAdapter] | None = None,
        *,
        auth_policy: GatewayAuthPolicy | None = None,
    ) -> None:
        self.adapters = adapters or default_mock_adapters()
        self.auth_policy = auth_policy or GatewayAuthPolicy()

    def receive(
        self,
        channel: GatewayChannel,
        user_id: str,
        text: str,
        *,
        thread_id: str | None = None,
        token: str | None = None,
        attachments: list[AttachmentMetadata] | None = None,
    ) -> MessageEvent:
        auth = self.auth_policy.authorize(channel, user_id, token=token)
        if not auth.allowed:
            raise ValueError(auth.reason_code)
        return self.adapters[channel].receive(
            user_id,
            text,
            thread_id=thread_id,
            attachments=attachments,
            authenticated=True,
        )

    def to_run_spec(self, event: MessageEvent, *, workspace: str = ".") -> RunSpec:
        return RunSpec(
            goal=event.text,
            workspace=workspace,
            mode="guarded",
            metadata={
                "gateway_event_id": event.id,
                "channel": event.channel,
                "user_id": event.user_id,
            },
        )

    def approval_card(
        self,
        channel: GatewayChannel,
        *,
        run_id: str,
        action_summary: str,
        risk: str,
        reason_codes: list[str],
    ) -> ApprovalCard:
        if risk not in {"medium", "high", "blocked"}:
            raise ValueError("approval risk must be medium, high, or blocked")
        card = ApprovalCard(
            channel=channel,
            run_id=run_id,
            action_summary=action_summary,
            risk=risk,  # type: ignore[arg-type]
            reason_codes=reason_codes,
        )
        return self.adapters[channel].send_approval(card)

    def decide(self, card: ApprovalCard, *, approve: bool) -> ApprovalCard:
        card.status = "approved" if approve else "denied"
        card.decided_at = utc_now()
        return card

    def resume_decision(self, card: ApprovalCard) -> ApprovalResumeDecision:
        if card.status == "pending":
            raise ValueError("approval card is still pending")
        return ApprovalResumeDecision(
            card_id=card.id,
            run_id=card.run_id,
            approve=card.status == "approved",
            deny=card.status == "denied",
            status=card.status,
            signal="approve" if card.status == "approved" else "deny",
        )

    def deliver(
        self,
        channel: GatewayChannel,
        user_id: str,
        summary: str,
        *,
        message_id: str | None = None,
    ) -> DeliveryRecord:
        return self.adapters[channel].deliver(user_id, summary, message_id=message_id)
