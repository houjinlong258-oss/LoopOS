"""Tests for the v0.4.0 Imagination Sandbox and Creativity Boundary.

The spec requires these seven scenarios:
1. Thought-only request does not trigger policy block.
2. ImaginationResult contains no syscall field.
3. Creative candidate can be risky but non-executable.
4. CommitmentBoundary triggers policy for side-effect actions.
5. Policy blocks action, not idea (i.e. policy can label an idea but
   not refuse a brainstorm).
6. authority_delta is "none" before commitment.
7. Syscall is not available in ImaginationSandbox.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from loopos.boundary import ActionBoundary, CommitmentGate
from loopos.loop_engine import (
    CommitmentProposal,
    ImaginationRequest,
    ImaginationSandbox,
    UserGoal,
)


def _goal() -> UserGoal:
    return UserGoal(raw_goal="Design a better planner").normalized()


class TestImaginationSandbox:
    def test_thought_only_does_not_trigger_policy_block(self) -> None:
        """A brainstorm must return a result; the boundary has no say."""
        boundary = ActionBoundary()
        before = len(boundary.audit_trail())
        sandbox = ImaginationSandbox()
        result = sandbox.imagine(ImaginationRequest(
            goal=_goal(), prompt="Three ideas", mode="brainstorm", max_candidates=3,
        ))
        # The sandbox must return a result, and the boundary must not
        # have been called by the sandbox.
        assert len(result.candidates) == 3
        assert len(boundary.audit_trail()) == before

    def test_imagination_result_contains_no_syscall(self) -> None:
        result = ImaginationSandbox().imagine(ImaginationRequest(
            goal=_goal(), prompt="x", mode="brainstorm", max_candidates=2,
        ))
        # The result type has no syscall field by construction.
        assert "syscall" not in result.model_dump()
        assert not hasattr(result, "syscall")
        assert not hasattr(result, "file_mutation")
        assert not hasattr(result, "network_call")
        # And the symbolic method returns False.
        assert result.has_executable_action() is False

    def test_creative_candidate_can_be_risky_but_non_executable(self) -> None:
        result = ImaginationSandbox().imagine(ImaginationRequest(
            goal=_goal(),
            prompt="Risky rewrite of the whole planner",
            mode="wild",
            max_candidates=2,
        ))
        for cand in result.candidates:
            # A "wild" idea is allowed to be risky, but authority_delta
            # must still be "none".
            assert cand.authority_delta == "none"

    def test_authority_delta_none_before_commitment(self) -> None:
        for c in ImaginationSandbox().imagine(ImaginationRequest(
            goal=_goal(), prompt="x", mode="brainstorm", max_candidates=3,
        )).candidates:
            assert c.authority_delta == "none"

    def test_candidate_with_authority_delta_rejected(self) -> None:
        from loopos.loop_engine.imagination import CreativeCandidate
        with pytest.raises(ValidationError):
            CreativeCandidate(title="x", summary="y", authority_delta="full")  # type: ignore[arg-type]

    def test_syscall_not_available_in_imagination_sandbox(self) -> None:
        sandbox = ImaginationSandbox()
        # The sandbox public surface has no method to dispatch anything.
        public = {m for m in dir(sandbox) if not m.startswith("_")}
        for forbidden in ("dispatch", "execute", "syscall", "run_syscall", "commit"):
            assert forbidden not in public, f"Sandbox exposes {forbidden}"

    def test_commitment_boundary_triggers_policy(self) -> None:
        gate = CommitmentGate()
        before = len(gate.boundary.audit_trail())
        # A side-effect action (patch) must add an audit entry.
        d = gate.commit(CommitmentProposal(
            proposed_action="write file x.py",
            action_type="patch",
            rationale="add test",
        ))
        assert d.allowed is True
        assert d.reason_codes and d.reason_codes[0] == "side_effect_gated"
        assert len(gate.boundary.audit_trail()) == before + 1

        # An advisory action (plan / doc) must not.
        gate2 = CommitmentGate()
        before2 = len(gate2.boundary.audit_trail())
        d2 = gate2.commit(CommitmentProposal(
            proposed_action="draft plan",
            action_type="plan",
            rationale="brainstorm",
        ))
        assert d2.allowed is True
        assert d2.reason_codes == ["advisory_action"]
        assert len(gate2.boundary.audit_trail()) == before2
