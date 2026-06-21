"""Tests for Maintainability Kernel models."""

from loopos.maintainability.models import (
    CodeChangeSummary,
    MaintainabilityFinding,
    MaintainabilityGateDecision,
    MaintainabilityReport,
)


def test_code_change_summary_defaults() -> None:
    s = CodeChangeSummary()
    assert s.summary_id
    assert s.changed_files == []
    assert s.added_lines == 0


def test_finding_creation() -> None:
    f = MaintainabilityFinding(
        category="large_diff",
        severity="warning",
        message="Too many lines.",
    )
    assert f.finding_id
    assert f.category == "large_diff"
    assert f.severity == "warning"


def test_report_defaults() -> None:
    r = MaintainabilityReport()
    assert r.score == 100.0
    assert r.recommendation == "approve"
    assert r.risk_level == "low"


def test_gate_decision_creation() -> None:
    d = MaintainabilityGateDecision(
        report_id="rpt_123",
        allowed_to_continue=False,
        blocks_merge=True,
        reason_codes=["blocker:policy_bypass"],
    )
    assert not d.allowed_to_continue
    assert d.blocks_merge
