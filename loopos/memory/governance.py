"""Memory governance review."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from loopos.memory.belief_store import MemoryItem
from loopos.memory.proposals import MemoryProposal

GovernanceAction = Literal["allow", "reject", "supersede", "warn", "merge"]


class GovernanceDecision(BaseModel):
    action: GovernanceAction
    reasons: list[str] = Field(default_factory=list)
    existing_id: str | None = None
    item: MemoryItem | None = None


class MemoryGovernance:
    """Validate, deduplicate, and score memory writes."""

    def __init__(self, *, min_confidence: float = 0.35) -> None:
        self.min_confidence = min_confidence

    def review(
        self,
        item: MemoryItem | MemoryProposal,
        existing: list[MemoryItem] | None = None,
    ) -> GovernanceDecision:
        if isinstance(item, MemoryProposal):
            return self.review_proposal(item, existing=existing)
        return self.review_item(item, existing=existing)

    def review_proposal(
        self,
        proposal: MemoryProposal,
        existing: list[MemoryItem] | None = None,
    ) -> GovernanceDecision:
        decision = self.review_item(proposal.proposed_item, existing=existing)
        if decision.action == "allow":
            decision.reasons.append("proposal accepted by governance")
        elif decision.action == "merge":
            decision.reasons.append("proposal should merge with existing memory")
        return decision

    def review_item(
        self,
        item: MemoryItem,
        existing: list[MemoryItem] | None = None,
    ) -> GovernanceDecision:
        item.tags = self._canonical_tags(item.tags)
        item.decay_score = self._decay_score(item)
        reasons: list[str] = []
        if item.confidence < self.min_confidence:
            reasons.append("confidence below write threshold")
        if not item.source.strip():
            reasons.append("missing source")
        if item.version < 1:
            reasons.append("invalid version")
        if item.layer == "skill" and item.type != "skill":
            reasons.append("skill layer requires memory type skill")
        if item.layer == "user_model" and item.scope not in {"user", "global"}:
            reasons.append("user_model layer requires user or global scope")

        for prior in existing or []:
            if prior.status != "active":
                continue
            same_content = (
                prior.type == item.type
                and self._normalize(prior.content) == self._normalize(item.content)
                and prior.scope == item.scope
                and prior.layer == item.layer
            )
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
                action="merge",
                reasons=["memory conflicts with existing active items"],
                item=item,
            )
        return GovernanceDecision(action="allow", item=item)

    @staticmethod
    def _canonical_tags(tags: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for tag in tags:
            normalized = tag.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
        return result

    @staticmethod
    def _normalize(content: str) -> str:
        return re.sub(r"\s+", " ", content.strip().lower())

    @staticmethod
    def _decay_score(item: MemoryItem) -> float:
        total = item.success_count + item.failure_count
        if total == 0:
            return item.decay_score
        success_ratio = item.success_count / total
        failure_penalty = item.failure_count / total
        return max(0.0, min(1.0, (item.decay_score * 0.7) + (success_ratio * 0.3) - (failure_penalty * 0.2)))
