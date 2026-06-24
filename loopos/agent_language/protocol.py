"""Protocol helpers for building LAIL signals."""

from __future__ import annotations

from typing import Any

from loopos.agent_language.message import Actionability, AgentMessage
from loopos.agent_language.roles import AgentRole


def make_signal(
    *,
    trace_id: str,
    iteration_id: str | int,
    from_role: AgentRole,
    to_role: AgentRole | list[AgentRole],
    signal_type: str,
    payload: dict[str, Any] | None = None,
    evidence: list[str] | None = None,
    confidence: float = 1.0,
    actionability: Actionability = Actionability.ADVISORY,
) -> AgentMessage:
    return AgentMessage(
        trace_id=trace_id,
        iteration_id=iteration_id,
        from_role=from_role,
        to_role=to_role,
        signal_type=signal_type,
        payload=payload or {},
        evidence=evidence or [],
        confidence=confidence,
        actionability=actionability,
        authority_delta="none",
    )


__all__ = ["make_signal"]
