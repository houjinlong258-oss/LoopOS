"""Persistent mock ChatOps message and approval store."""

from __future__ import annotations

import json
from pathlib import Path

from loopos.gateway.models import ApprovalCard, ApprovalResumeDecision, MessageEvent, utc_now


class GatewayStore:
    def __init__(self, *, messages_path: str | Path, approvals_path: str | Path) -> None:
        self.messages_path = Path(messages_path)
        self.approvals_path = Path(approvals_path)
        self.messages_path.parent.mkdir(parents=True, exist_ok=True)
        self.approvals_path.parent.mkdir(parents=True, exist_ok=True)

    def list_messages(self) -> list[MessageEvent]:
        if not self.messages_path.exists():
            return []
        rows = json.loads(self.messages_path.read_text(encoding="utf-8") or "[]")
        return [MessageEvent.model_validate(item) for item in rows]

    def append_message(self, event: MessageEvent) -> MessageEvent:
        rows = [item.model_dump(mode="json") for item in self.list_messages()]
        rows.append(event.model_dump(mode="json"))
        self.messages_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        return event

    def list_approvals(self) -> list[ApprovalCard]:
        if not self.approvals_path.exists():
            return []
        rows = json.loads(self.approvals_path.read_text(encoding="utf-8") or "[]")
        return [ApprovalCard.model_validate(item) for item in rows]

    def load_approval(self, card_id: str) -> ApprovalCard:
        for card in self.list_approvals():
            if card.id == card_id:
                return card
        raise KeyError(f"approval card not found: {card_id}")

    def save_approval(self, card: ApprovalCard) -> ApprovalCard:
        cards = {item.id: item for item in self.list_approvals()}
        card.updated_at = utc_now()
        cards[card.id] = card
        self.approvals_path.write_text(
            json.dumps(
                [item.model_dump(mode="json") for item in cards.values()],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return card

    def decide(self, card_id: str, *, approve: bool) -> ApprovalResumeDecision:
        card = self.load_approval(card_id)
        card.status = "approved" if approve else "denied"
        card.decided_at = utc_now()
        self.save_approval(card)
        return ApprovalResumeDecision(
            card_id=card.id,
            run_id=card.run_id,
            approve=approve,
            deny=not approve,
            status=card.status,
        )

