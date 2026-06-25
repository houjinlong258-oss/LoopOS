"""Feishu adapter contract without real message sending."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FeishuAdapter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter_id: str = "feishu"
    sent_messages: list[str] = Field(default_factory=list)

    def send_message(self, text: str, *, allow_send: bool = False) -> dict[str, object]:
        if not allow_send:
            return {"status": "dry_run", "sent": False, "text": text}
        self.sent_messages.append(text)
        return {"status": "sent", "sent": True, "text": text}


__all__ = ["FeishuAdapter"]
