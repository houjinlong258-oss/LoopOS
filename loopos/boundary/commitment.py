"""Commitment gate: bridges ``CommitmentProposal`` to ``ActionBoundary``.

The ``CommitmentGate`` is the v0.4.0 wrapper that combines the
``CommitmentBoundary`` (from ``loopos.loop_engine``) with the
``ActionBoundary``. It is the single entry point the loop uses
when an idea is being promoted to an action.
"""

from __future__ import annotations

from loopos.boundary.action_boundary import ActionBoundary, ActionBoundaryDecision
from loopos.loop_engine.commitment import (
    CommitmentBoundary,
    CommitmentDecision,
    CommitmentProposal,
    SIDE_EFFECT_ACTIONS,
)


class CommitmentGate:
    """Validate a ``CommitmentProposal`` and forward side-effect actions."""

    def __init__(
        self,
        boundary: ActionBoundary | None = None,
        commitment_boundary: CommitmentBoundary | None = None,
    ) -> None:
        self.boundary = boundary or ActionBoundary()
        self.commitment_boundary = commitment_boundary or CommitmentBoundary()

    def commit(self, proposal: CommitmentProposal) -> CommitmentDecision:
        decision = self.commitment_boundary.commit(proposal)
        if decision.allowed and proposal.action_type in SIDE_EFFECT_ACTIONS:
            # Side-effect actions additionally go through the action
            # boundary so the audit trail captures the dispatch.
            self.boundary.evaluate(
                action=proposal.proposed_action,
                action_type=proposal.action_type,
                required_permissions=proposal.required_permissions,
            )
        return decision


__all__ = ["CommitmentGate"]


# Re-export for type checkers
_ = ActionBoundaryDecision
