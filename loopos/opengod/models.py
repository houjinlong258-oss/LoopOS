"""OpenGod data models.

OpenGod is a strategic meta-agent that emits **decisions**, not
commands. The decision kind is a closed set that the rest of the
runtime can route on. The verdict wraps the decision with a
status + reason-codes so the Workbench can render it.

Decision kinds
--------------

* ``single_agent``         — one native agent session
* ``adapter_agent``        — one adapter-driven session
* ``fusion_pair``          — two competing agents
* ``fusion_committee``     — N agents, vote
* ``mad_dog``              — explicit escalation
* ``ask_user``             — wait for human
* ``halt``                 — stop with a reason
* ``needs_repair``         — submit ``repair.plan``
* ``needs_replan``         — submit ``goal.replan``
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


OpenGodDecisionKind = Literal[
    "single_agent",
    "adapter_agent",
    "fusion_pair",
    "fusion_committee",
    "mad_dog",
    "ask_user",
    "halt",
    "needs_repair",
    "needs_replan",
]


OpenGodVerdictStatus = Literal[
    "ok",
    "needs_repair",
    "needs_replan",
    "ask_user",
    "halted",
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OpenGodContext(BaseModel):
    """Read-only view of the runtime handed to OpenGod."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "0.3"
    goal_id: str
    goal_title: str = ""
    goal_risk: str = "medium"
    trace_event_count: int = 0
    dropped_event_count: int = 0
    replay_status: str = "unknown"  # "pass" | "fail" | "unknown" | "skipped"
    readiness_status: str = "unknown"  # "pass" | "warn" | "fail" | "unknown"
    hard_fail_count: int = 0
    fusion_mode: str = "single"  # "single" | "pair" | "committee" | "mad_dog"
    fusion_score: int = 0
    adapter_id: str = ""
    live_provider_calls: bool = False
    budget_used_usd: float = 0.0
    budget_max_usd: float = 0.0
    extra: dict[str, Any] = Field(default_factory=dict)


class OpenGodDecision(BaseModel):
    """Strategic decision emitted by OpenGod."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "0.3"
    decision_id: str = Field(default_factory=lambda: f"ogd_{uuid4().hex[:10]}")
    goal_id: str
    kind: OpenGodDecisionKind
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reason_codes: list[str] = Field(default_factory=list)
    rationale: str = ""
    created_at: datetime = Field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class OpenGodVerdict(BaseModel):
    """Final actionable verdict wrapping a decision."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "0.3"
    verdict_id: str = Field(default_factory=lambda: f"ogv_{uuid4().hex[:10]}")
    status: OpenGodVerdictStatus
    decision: OpenGodDecision
    next_action: str = ""  # human-readable next step
    blocked: bool = False
    reason_codes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


__all__ = [
    "OpenGodContext",
    "OpenGodDecision",
    "OpenGodDecisionKind",
    "OpenGodVerdict",
    "OpenGodVerdictStatus",
]
