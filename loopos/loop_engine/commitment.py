"""Commitment Boundary: gates the transition from idea to action.

Only ``CommitmentProposal`` instances that have passed
``CommitmentBoundary.commit()`` may produce real side effects. The
boundary is deterministic for a given ``(proposal, action_type)`` pair
in v0.4.0.
"""

from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from loopos.loop_engine.models import UserGoal  # noqa: F401  (re-export)


ActionType = Literal[
    "plan", "patch", "test", "command",
    "syscall", "release", "doc",
]


# Action types that map to real side effects. ``plan`` and ``doc`` are
# advisory and do not trigger hard policy / syscall routing.
SIDE_EFFECT_ACTIONS: frozenset[ActionType] = frozenset({
    "patch", "test", "command", "syscall", "release",
})


class CommitmentProposal(BaseModel):
    """A typed proposal to bridge an idea to an action."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"commit_{uuid4().hex[:8]}")
    source_candidate_id: str | None = None
    proposed_action: str
    action_type: ActionType
    expected_side_effects: list[str] = Field(default_factory=list)
    required_permissions: list[str] = Field(default_factory=list)
    requires_policy: bool = True
    requires_approval: bool = False
    rationale: str = ""

    def has_side_effect(self) -> bool:
        return self.action_type in SIDE_EFFECT_ACTIONS


class CommitmentDecision(BaseModel):
    """A structured decision on a ``CommitmentProposal``."""

    model_config = ConfigDict(extra="forbid")

    allowed: bool
    requires_approval: bool
    reason_codes: list[str] = Field(default_factory=list)
    risk_label: str = "low"
    constraints: list[str] = Field(default_factory=list)
    audit_id: str = Field(default_factory=lambda: f"audit_{uuid4().hex[:8]}")


class CommitmentBoundary:
    """The v0.4.0 deterministic commitment gate.

    The decision is a pure function of the proposal in v0.4.0:

    * ``plan`` and ``doc`` actions are always allowed without policy
      check; they are advisory.
    * Side-effect actions are allowed by default in v0.4.0 (the
      actual policy / syscall routing lives in ``loopos.boundary`` and
      ``loopos.policy_os``), but the decision records that the
      proposal is **gated** so the audit trail is complete.
    """

    def commit(self, proposal: CommitmentProposal) -> CommitmentDecision:
        if not proposal.has_side_effect():
            return CommitmentDecision(
                allowed=True,
                requires_approval=False,
                reason_codes=["advisory_action"],
                risk_label="low",
            )
        # Side-effect action: allowed by default in v0.4.0 simulated
        # mode, but flagged as gated.
        return CommitmentDecision(
            allowed=True,
            requires_approval=proposal.requires_approval,
            reason_codes=["side_effect_gated"],
            risk_label="medium" if not proposal.requires_approval else "high",
            constraints=["dispatch_via_action_boundary"],
        )


__all__ = [
    "ActionType",
    "CommitmentBoundary",
    "CommitmentDecision",
    "CommitmentProposal",
    "SIDE_EFFECT_ACTIONS",
]
