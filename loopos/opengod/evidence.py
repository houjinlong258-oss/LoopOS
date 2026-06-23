"""OpenGod evidence collection.

The :class:`collect_evidence` helper builds an :class:`OpenGodContext`
from a set of optional runtime sources:

* a goal spec (``goal_id``, ``title``, ``risk``),
* a trace summary (``event_count``, ``dropped_count``, ``replay_status``),
* a readiness summary (``status``, ``hard_fail_count``),
* a fusion summary (``mode``, ``score``),
* a budget summary.

All inputs are optional; missing inputs default to safe values so a
fresh test can call :func:`collect_evidence` with just a goal id.
"""

from __future__ import annotations

from typing import Any

from loopos.opengod.models import OpenGodContext


def collect_evidence(
    *,
    goal_id: str,
    goal_title: str = "",
    goal_risk: str = "medium",
    trace_event_count: int = 0,
    dropped_event_count: int = 0,
    replay_status: str = "unknown",
    readiness_status: str = "unknown",
    hard_fail_count: int = 0,
    fusion_mode: str = "single",
    fusion_score: int = 0,
    adapter_id: str = "",
    live_provider_calls: bool = False,
    budget_used_usd: float = 0.0,
    budget_max_usd: float = 0.0,
    extra: dict[str, Any] | None = None,
) -> OpenGodContext:
    """Build a context from a flat set of inputs."""
    return OpenGodContext(
        goal_id=goal_id,
        goal_title=goal_title,
        goal_risk=goal_risk,
        trace_event_count=trace_event_count,
        dropped_event_count=dropped_event_count,
        replay_status=replay_status,
        readiness_status=readiness_status,
        hard_fail_count=hard_fail_count,
        fusion_mode=fusion_mode,
        fusion_score=fusion_score,
        adapter_id=adapter_id,
        live_provider_calls=live_provider_calls,
        budget_used_usd=budget_used_usd,
        budget_max_usd=budget_max_usd,
        extra=dict(extra or {}),
    )


class OpenGodEvidence:
    """Bag-of-evidence alias kept for documentation and forward-compat.

    The collected context is already an immutable evidence record;
    this class is just a typed alias for places that want to be
    explicit about role.
    """

    __slots__ = ("context",)

    def __init__(self, context: OpenGodContext) -> None:
        self.context = context

    def to_context(self) -> OpenGodContext:
        return self.context


__all__ = ["OpenGodEvidence", "collect_evidence"]
