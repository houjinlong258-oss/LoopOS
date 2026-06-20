"""ChatOps gateway router for mock mobile/chat adapters."""

from __future__ import annotations

from loopos.gateway.adapters import MockGatewayAdapter, default_mock_adapters
from loopos.gateway.models import ApprovalCard, GatewayChannel, MessageEvent
from loopos.kernel.models import RunSpec


class ChatOpsGateway:
    def __init__(self, adapters: dict[GatewayChannel, MockGatewayAdapter] | None = None) -> None:
        self.adapters = adapters or default_mock_adapters()

    def receive(
        self,
        channel: GatewayChannel,
        user_id: str,
        text: str,
        *,
        thread_id: str | None = None,
    ) -> MessageEvent:
        return self.adapters[channel].receive(user_id, text, thread_id=thread_id)

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
        return card

