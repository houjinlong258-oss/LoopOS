"""Unified Memory OS repository."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from loopos.core.state import LoopState, utc_now
from loopos.memory.belief_store import BeliefStore, MemoryItem, MemoryStatus
from loopos.memory.event_log import EventLog
from loopos.memory.governance import GovernanceDecision, MemoryGovernance
from loopos.memory.proposals import MemoryProposal, ProposalStatus
from loopos.memory.retrieval import MemoryRetriever
from loopos.memory.skill_store import SkillStore
from loopos.memory.sqlite_store import SQLiteMemoryIndex
from loopos.memory.state_store import StateStore
from loopos.policy_os.engine import PolicyEngine

ProposalDecision = Literal["accepted", "rejected", "merged"]


class MemoryRepository:
    """JSONL + SQLite memory facade."""

    def __init__(
        self,
        base_dir: str | Path = ".loopos",
        *,
        policy_engine: PolicyEngine | None = None,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.events = EventLog(self.base_dir / "events.jsonl")
        self.states = StateStore(self.base_dir / "runs")
        self.beliefs = BeliefStore(self.base_dir / "beliefs.jsonl")
        self.skills = SkillStore(self.base_dir / "skills.jsonl")
        self.index = SQLiteMemoryIndex(self.base_dir / "memory.sqlite3")
        self.governance = MemoryGovernance()
        self.policy_engine = policy_engine or PolicyEngine.load_default()

    def save_state(self, state: LoopState) -> None:
        self.states.save(state)
        self.index.upsert_run(state)

    def write_memory(self, item: MemoryItem) -> GovernanceDecision:
        policy_decision = self.policy_engine.evaluate(
            "memory.write",
            subject=item.model_dump(mode="json"),
            tags=["memory", item.layer, item.scope],
            risk_level="medium" if item.scope == "global" else "low",
        )
        if not policy_decision.allowed:
            return GovernanceDecision(
                action="reject",
                reasons=[f"policy {policy_decision.action}: {', '.join(policy_decision.reason_codes)}"],
                item=item,
            )
        existing = self.list_memory(status="active")
        decision = self.governance.review(item, existing=existing)
        if decision.action in {"allow", "warn", "merge"} and decision.item is not None:
            accepted = decision.item
            if decision.action == "merge":
                accepted.status = "conflicted"
            self.beliefs.add(accepted)
            self.index.upsert_memory_item(accepted)
        return decision

    def propose(self, proposal: MemoryProposal) -> MemoryProposal:
        self.index.upsert_proposal(proposal)
        return proposal

    def list_proposals(self, *, status: ProposalStatus | None = None) -> list[MemoryProposal]:
        return self.index.list_proposals(status=status)

    def decide_proposal(
        self,
        proposal_id: str,
        decision: ProposalDecision,
        *,
        reasons: list[str] | None = None,
    ) -> MemoryProposal:
        proposal = self.index.get_proposal(proposal_id)
        proposal.status = decision
        proposal.decision_reasons = reasons or []
        proposal.decided_at = utc_now()
        if decision in {"accepted", "merged"}:
            governance_decision = self.write_memory(proposal.proposed_item)
            proposal.decision_reasons.extend(governance_decision.reasons)
            if governance_decision.action == "reject":
                proposal.status = "rejected"
        self.index.upsert_proposal(proposal)
        return proposal

    def list_memory(
        self,
        *,
        status: MemoryStatus | None = None,
        layer: str | None = None,
        scope: str | None = None,
        limit: int | None = None,
    ) -> list[MemoryItem]:
        return self.index.list_memory(status=status, layer=layer, scope=scope, limit=limit)

    def retrieve(
        self,
        *,
        query_text: str = "",
        tags: list[str] | None = None,
        layer: str | None = None,
        scope: str | None = None,
        status: MemoryStatus = "active",
        limit: int = 5,
        min_confidence: float = 0.0,
    ) -> list[MemoryItem]:
        candidates = self.list_memory(status=status, layer=layer, scope=scope)
        return MemoryRetriever(candidates).retrieve(
            tags or [],
            query_text=query_text,
            limit=limit,
            min_confidence=min_confidence,
        )

    def reindex(self) -> dict[str, int]:
        self.index.reset_index()
        counts = {"runs": 0, "events": 0, "memory_items": 0, "skills": 0}
        for run_id in self.states.list_run_ids():
            self.index.upsert_run(self.states.load(run_id))
            counts["runs"] += 1
        for event in self.events.list():
            self.index.upsert_event(event)
            counts["events"] += 1
        for item in self.beliefs.list():
            self.index.upsert_memory_item(item)
            counts["memory_items"] += 1
        for skill in self.skills.list():
            self.index.upsert_skill(skill)
            counts["skills"] += 1
        return counts

    def set_profile(self, key: str, value: str) -> None:
        self.index.set_profile(key, value, updated_at=str(utc_now()))
        item = MemoryItem(
            type="user_model",
            layer="user_model",
            scope="user",
            content=f"{key}: {value}",
            confidence=1.0,
            source="user_profile",
            tags=["user", "profile", key.lower()],
            metadata={"key": key, "value": value},
        )
        self.write_memory(item)

    def get_profile(self) -> dict[str, str]:
        return self.index.get_profile()

    def proposal_for_run(self, run_id: str) -> MemoryProposal:
        events = self.events.list(run_id)
        content = f"Run {run_id} produced {len(events)} events."
        item = MemoryItem(
            type="fact",
            layer="episodic",
            scope="project",
            content=content,
            confidence=0.6,
            source="memory_proposal_extractor",
            tags=["run", "episodic"],
        )
        return MemoryProposal(
            proposed_item=item,
            source="mock",
            source_run_id=run_id,
            source_event_ids=[event.id for event in events],
            rationale="Deterministic proposal from run history.",
        )
