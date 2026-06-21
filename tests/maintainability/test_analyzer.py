"""Tests for the maintainability analyzer and gate."""

from loopos.maintainability.analyzer import MaintainabilityAnalyzer
from loopos.maintainability.gate import MaintainabilityGate
from loopos.maintainability.models import CodeChangeSummary


def test_analyzer_clean_change() -> None:
    summary = CodeChangeSummary(
        changed_files=["loopos/core/models.py", "tests/test_models.py"],
        test_files_changed=["tests/test_models.py"],
        added_lines=30,
        removed_lines=5,
    )
    report = MaintainabilityAnalyzer().analyze(summary)
    assert report.score >= 90
    assert report.recommendation == "approve"


def test_analyzer_large_diff_lowers_score() -> None:
    summary = CodeChangeSummary(
        changed_files=["loopos/kernel/big.py"],
        added_lines=500,
        removed_lines=400,
    )
    report = MaintainabilityAnalyzer().analyze(summary)
    assert report.score < 90


def test_analyzer_policy_bypass_blocks() -> None:
    summary = CodeChangeSummary(
        changed_files=["loopos/runner.py"],
        test_files_changed=["tests/test_runner.py"],
        added_lines=10,
    )
    files = {
        "loopos/runner.py": 'import subprocess\nsubprocess.run(["ls"])\n'
    }
    report = MaintainabilityAnalyzer().analyze(summary, files=files)
    assert report.score == 0
    assert report.recommendation == "block"


def test_gate_allows_clean() -> None:
    summary = CodeChangeSummary(
        changed_files=["loopos/core/x.py", "tests/test_x.py"],
        test_files_changed=["tests/test_x.py"],
        added_lines=20,
    )
    report = MaintainabilityAnalyzer().analyze(summary)
    decision = MaintainabilityGate().evaluate(report)
    assert decision.allowed_to_continue
    assert not decision.blocks_merge


def test_gate_blocks_bypass() -> None:
    summary = CodeChangeSummary(
        changed_files=["loopos/runner.py"],
        test_files_changed=["tests/test_runner.py"],
        added_lines=5,
    )
    files = {
        "loopos/runner.py": 'import os\nos.system("ls")\n'
    }
    report = MaintainabilityAnalyzer().analyze(summary, files=files)
    decision = MaintainabilityGate().evaluate(report)
    assert not decision.allowed_to_continue
    assert decision.blocks_merge


def test_gate_requests_changes_for_low_score() -> None:
    summary = CodeChangeSummary(
        changed_files=["loopos/a.py", "loopos/b.py"],
        added_lines=400,
        removed_lines=300,
    )
    report = MaintainabilityAnalyzer().analyze(summary)
    decision = MaintainabilityGate().evaluate(report)
    # Score should be <90 due to large_diff + missing_tests
    assert not decision.allowed_to_continue or decision.requires_human_review


def test_report_json_serializable() -> None:
    summary = CodeChangeSummary(added_lines=10, changed_files=["x.py"])
    report = MaintainabilityAnalyzer().analyze(summary)
    data = report.model_dump(mode="json")
    assert "score" in data
    assert "findings" in data
    assert "recommendation" in data
