"""Tests for the Fusion Verdict Orchestrator."""

from __future__ import annotations

from typing import Any

from loopos.fusion_router import (
    FusionVerdict,
    FusionVerdictOrchestrator,
    OrchestrationResult,
)


def test_needs_repair_submits_noop_to_ali_repairing() -> None:
    v = FusionVerdict.model_validate(
        {"fusion_id": "f1", "status": "needs_repair", "confidence": 0.5}
    )
    o = FusionVerdictOrchestrator()
    r = o.orchestrate(v)
    assert isinstance(r, OrchestrationResult)
    assert r.status == "submitted"
    assert r.next_ali_state == "REPAIRING"
    assert r.command is not None
    assert r.command.purpose == "repair.plan"
    assert r.command_result is not None


def test_needs_replan_submits_noop_to_ali_replanning() -> None:
    v = FusionVerdict.model_validate(
        {"fusion_id": "f1", "status": "needs_replan", "confidence": 0.5}
    )
    o = FusionVerdictOrchestrator()
    r = o.orchestrate(v)
    assert r.status == "submitted"
    assert r.next_ali_state == "REPLANNING"
    assert r.command is not None
    assert r.command.purpose == "goal.replan"


def test_rejected_halts_without_submitting() -> None:
    v = FusionVerdict.model_validate(
        {"fusion_id": "f1", "status": "rejected", "confidence": 0.5}
    )
    o = FusionVerdictOrchestrator()
    r = o.orchestrate(v)
    assert r.status == "halted"
    assert r.next_ali_state == "HALTED_FAILURE"
    assert r.command is None


def test_ask_user_waits_for_approval() -> None:
    v = FusionVerdict.model_validate(
        {"fusion_id": "f1", "status": "ask_user", "confidence": 0.5}
    )
    o = FusionVerdictOrchestrator()
    r = o.orchestrate(v)
    assert r.status == "no_action"
    assert r.next_ali_state == "WAITING_APPROVAL"


def test_accepted_status_is_no_action() -> None:
    v = FusionVerdict.model_validate(
        {"fusion_id": "f1", "status": "accepted", "confidence": 0.5}
    )
    o = FusionVerdictOrchestrator()
    r = o.orchestrate(v)
    assert r.status == "no_action"
    assert r.next_ali_state == ""


def test_orchestrator_uses_dry_run() -> None:
    """Regression: the orchestrator's ``explain`` kwarg polarity must
    match the v0.2 runner. ``dry_run=True`` must short-circuit; only
    ``dry_run=False`` should run the command for real."""
    class SpyRunner:
        def __init__(self) -> None:
            self.explain_calls: list[bool] = []

        def run(self, command: Any, *, explain: bool = False) -> Any:
            self.explain_calls.append(explain)
            from loopos.aci.models import AgentCommandResult
            from loopos.policy_os.models import PolicyDecision
            return AgentCommandResult(
                schema_version="0.2",
                command_id=command.id,
                goal_id=command.goal_id,
                status="dry_run" if explain else "completed",
                policy_decision=PolicyDecision(allowed=not explain, action="allow"),
            )

    v = FusionVerdict.model_validate(
        {"fusion_id": "f1", "status": "needs_repair", "confidence": 0.5}
    )
    runner = SpyRunner()
    o = FusionVerdictOrchestrator(runner=runner)  # type: ignore[arg-type]
    o.orchestrate(v, dry_run=True)
    assert runner.explain_calls == [True], "dry_run=True should pass explain=True"
    runner.explain_calls.clear()
    o.orchestrate(v, dry_run=False)
    assert runner.explain_calls == [False], "dry_run=False should pass explain=False"
