"""Tests for ``loopos.opengod``."""

from __future__ import annotations

from typing import Any

from loopos.opengod import (
    OpenGodBudgetGuard,
    collect_evidence,
    decide,
)


def test_default_decision_is_single_agent() -> None:
    ctx = collect_evidence(goal_id="g1")
    d = decide(ctx)
    assert d.kind == "single_agent"
    assert 0.0 <= d.confidence <= 1.0


def test_mad_dog_fusion_chooses_mad_dog() -> None:
    ctx = collect_evidence(goal_id="g1", fusion_mode="mad_dog", fusion_score=80)
    d = decide(ctx)
    assert d.kind == "mad_dog"
    assert "fusion_mad_dog" in d.reason_codes


def test_fusion_pair_chooses_fusion_pair() -> None:
    ctx = collect_evidence(goal_id="g1", fusion_mode="pair", fusion_score=42)
    d = decide(ctx)
    assert d.kind == "fusion_pair"


def test_fusion_committee_chooses_fusion_committee() -> None:
    ctx = collect_evidence(goal_id="g1", fusion_mode="committee", fusion_score=42)
    d = decide(ctx)
    assert d.kind == "fusion_committee"


def test_hard_fail_triggers_halt() -> None:
    ctx = collect_evidence(goal_id="g1", hard_fail_count=2)
    d = decide(ctx)
    assert d.kind == "halt"
    assert "hard_fail_present" in d.reason_codes


def test_readiness_fail_triggers_halt() -> None:
    ctx = collect_evidence(goal_id="g1", readiness_status="fail")
    d = decide(ctx)
    assert d.kind == "halt"
    assert "readiness_failed" in d.reason_codes


def test_replay_fail_triggers_repair() -> None:
    ctx = collect_evidence(goal_id="g1", replay_status="fail")
    d = decide(ctx)
    assert d.kind == "needs_repair"
    assert "replay_failed" in d.reason_codes


def test_adapter_attached_chooses_adapter_agent() -> None:
    ctx = collect_evidence(goal_id="g1", adapter_id="hermes")
    d = decide(ctx)
    assert d.kind == "adapter_agent"
    assert "adapter_present" in d.reason_codes


def test_verdict_status_mapping() -> None:
    """Each kind produces the right verdict status."""
    from loopos.opengod.verdict import _STATUS_FOR
    expected: dict[Any, str] = {
        "single_agent": "ok",
        "adapter_agent": "ok",
        "fusion_pair": "ok",
        "fusion_committee": "ok",
        "mad_dog": "ok",
        "ask_user": "ask_user",
        "halt": "halted",
        "needs_repair": "needs_repair",
        "needs_replan": "needs_replan",
    }
    for kind, want in expected.items():
        assert _STATUS_FOR[kind] == want, f"kind={kind} -> {_STATUS_FOR[kind]}"


def test_verdict_blocked_for_halt_and_ask_user() -> None:
    """halt and ask_user are blocked at the verdict layer."""
    from loopos.opengod.models import (
        OpenGodDecision,
    )
    from loopos.opengod.verdict import build_verdict
    for kind in ("halt", "ask_user"):
        d = OpenGodDecision(goal_id="g1", kind=kind)  # type: ignore[arg-type]
        v = build_verdict(d)
        assert v.blocked is True


def test_opengod_decision_for_halt() -> None:
    """Verify verdict mapping for the halt kind."""
    from loopos.opengod.verdict import _STATUS_FOR
    assert _STATUS_FOR["halt"] == "halted"


def test_budget_guard_blocks_over_budget() -> None:
    guard = OpenGodBudgetGuard(max_usd=1.0, reserve_usd=0.20)
    ctx = collect_evidence(goal_id="g1", fusion_mode="mad_dog", budget_used_usd=0.85)
    d = decide(ctx)
    a = guard.assess(ctx, d, estimated_live_calls=1)
    assert not a.allowed
    assert "opengod_budget_exceeded" in a.reason_codes


def test_budget_guard_blocks_when_reserve_exceeds_max() -> None:
    """Regression: when ``reserve_usd > max_usd`` (degenerate config)
    the ceiling is non-positive and the guard must still block on
    any non-zero spend. Previously the chained comparison
    ``projected > ceiling > 0`` short-circuited to ``False`` and
    allowed the call through."""
    guard = OpenGodBudgetGuard(max_usd=0.1, reserve_usd=0.5)
    ctx = collect_evidence(
        goal_id="g1", fusion_mode="mad_dog", budget_used_usd=0.0,
    )
    d = decide(ctx)
    a = guard.assess(ctx, d, estimated_live_calls=1)
    assert not a.allowed
    assert "opengod_budget_exceeded" in a.reason_codes


def test_budget_guard_allows_zero_spend_with_no_headroom() -> None:
    """With no live-spend decision, the guard returns allowed=True
    regardless of the headroom. The bug fix only changes behaviour
    for live-spend decisions."""
    guard = OpenGodBudgetGuard(max_usd=0.1, reserve_usd=0.5)
    ctx = collect_evidence(goal_id="g1")  # default: no fusion, no live
    d = decide(ctx)
    a = guard.assess(ctx, d, estimated_live_calls=1)
    assert a.allowed
    assert a.reason_codes == ["no_live_spend"]


def test_decide_returns_needs_replan_on_replay_skipped() -> None:
    ctx = collect_evidence(goal_id="g1", replay_status="skipped")
    d = decide(ctx)
    assert d.kind == "needs_replan"
    assert "replay_skipped" in d.reason_codes


def test_decide_asks_user_when_no_budget_but_live_requested() -> None:
    ctx = collect_evidence(
        goal_id="g1", live_provider_calls=True, budget_max_usd=0.0
    )
    d = decide(ctx)
    assert d.kind == "ask_user"
    assert "no_budget" in d.reason_codes


def test_budget_guard_allows_no_spend_decisions() -> None:
    guard = OpenGodBudgetGuard(max_usd=0.0)
    ctx = collect_evidence(goal_id="g1")
    d = decide(ctx)
    a = guard.assess(ctx, d, estimated_live_calls=1)
    assert a.allowed
    assert "no_live_spend" in a.reason_codes


def test_decision_is_pure() -> None:
    ctx = collect_evidence(goal_id="g1", fusion_mode="mad_dog")
    a = decide(ctx)
    b = decide(ctx)
    assert a.kind == b.kind
    assert a.reason_codes == b.reason_codes


def test_decision_confidence_in_range() -> None:
    for fusion_mode in ("single", "pair", "committee", "mad_dog"):
        ctx = collect_evidence(goal_id="g1", fusion_mode=fusion_mode)
        d = decide(ctx)
        assert 0.0 <= d.confidence <= 1.0
