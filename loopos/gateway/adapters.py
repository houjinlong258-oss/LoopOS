"""Mock ChatOps adapters."""

from __future__ import annotations

from loopos.gateway.models import ApprovalCard, GatewayChannel, MessageEvent

_MOCK_CHANNELS: list[GatewayChannel] = [
    "webhook",
    "telegram",
    "email",
    "slack",
    "discord",
    "whatsapp_cloud",
]


class MockGatewayAdapter:
    def __init__(self, channel: GatewayChannel) -> None:
        self.channel = channel
        self.messages: list[MessageEvent] = []
        self.approvals: list[ApprovalCard] = []

    def receive(self, user_id: str, text: str, *, thread_id: str | None = None) -> MessageEvent:
        event = MessageEvent(
            channel=self.channel,
            user_id=user_id,
            text=text,
            thread_id=thread_id,
        )
        self.messages.append(event)
        return event

    def send_approval(self, card: ApprovalCard) -> ApprovalCard:
        if card.channel != self.channel:
            raise ValueError("approval card channel does not match adapter")
        self.approvals.append(card)
        return card


def default_mock_adapters() -> dict[GatewayChannel, MockGatewayAdapter]:
    return {channel: MockGatewayAdapter(channel) for channel in _MOCK_CHANNELS}
