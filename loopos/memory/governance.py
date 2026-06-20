"""Memory governance review."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from loopos.memory.belief_store import MemoryItem

GovernanceAction = Literal["allow", "reject", "supersede", "warn"]


class GovernanceDecision(BaseModel):
    action: GovernanceAction
    reasons: list[str] = Field(default_factory=list)
    existing_id: str | None = None
    item: MemoryItem | None = None


class MemoryGovernance:
    """Validate, deduplicate, and score memory writes."""

    def __init__(self, *, min_confidence: float = 0.35) -> None:
        self.min_confidence = min_confidence

    def review(self, item: MemoryItem, existing: list[MemoryItem] | None = None) -> GovernanceDecision:
        reasons: list[str] = []
        if item.confidence < self.min_confidence:
            reasons.append("confidence below write threshold")
        if not item.source.strip():
            reasons.append("missing source")
        if item.version < 1:
            reasons.append("invalid version")

        for prior in existing or []:
            if prior.status != "active":
                continue
            same_content = prior.type == item.type and prior.content.strip() == item.content.strip()
            tag_overlap = set(prior.tags).intersection(item.tags)
            if same_content:
                return GovernanceDecision(
                    action="reject",
                    reasons=["duplicate active memory"],
                    existing_id=prior.id,
                    item=item,
                )
            if tag_overlap and prior.content.strip() != item.content.strip():
                item.conflicts.append(prior.id)

        if reasons:
            return GovernanceDecision(action="reject", reasons=reasons, item=item)
        if item.conflicts:
            item.status = "conflicted"
            return GovernanceDecision(
                action="warn",
                reasons=["memory conflicts with existing active items"],
                item=item,
            )
        return GovernanceDecision(action="allow", item=item)
