"""In-memory trace for LAIL messages."""

from __future__ import annotations

from loopos.agent_language.message import AgentMessage


class AgentMessageTrace:
    def __init__(self) -> None:
        self._items: list[AgentMessage] = []

    def record(self, message: AgentMessage) -> AgentMessage:
        self._items.append(message)
        return message

    def list(self, trace_id: str | None = None) -> list[AgentMessage]:
        if trace_id is None:
            return list(self._items)
        return [item for item in self._items if item.trace_id == trace_id]


__all__ = ["AgentMessageTrace"]
