"""Tests for Review Artifact and Merge Gate."""

from loopos.review.artifact import MergeGateDecision, ReviewArtifact
from loopos.review.gate import MergeGate, ReviewArtifactBuilder


def test_artifact_creation() -> None:
    a = ReviewArtifact(run_id="run-1")
    assert a.artifact_id
    assert a.decision == "approve"


def test_builder_approve_clean() -> None:
    builder = ReviewArtifactBuilder("run-1")
    builder.set_diff_summary({"files": 2})
    builder.add_test_result({"name": "test_x", "passed": True})
    builder.set_acceptance({"goal_met": "passed"})
    artifact = builder.build()
    assert artifact.decision == "approve"


def test_builder_reject_on_failed_acceptance() -> None:
    builder = ReviewArtifactBuilder("run-1")
    builder.set_acceptance({"goal_met": "failed"})
    artifact = builder.build()
    assert artifact.decision == "reject"


def test_builder_blocked_on_policy() -> None:
    builder = ReviewArtifactBuilder("run-1")
    builder.add_policy_check({"rule": "L5", "allowed": False, "severity": "blocker"})
    artifact = builder.build()
    assert artifact.decision == "blocked"


def test_builder_request_changes_on_findings() -> None:
    builder = ReviewArtifactBuilder("run-1")
    builder.add_finding("Missing error handling")
    artifact = builder.build()
    assert artifact.decision == "request_changes"


def test_merge_gate_allows_clean() -> None:
    builder = ReviewArtifactBuilder("run-1")
    builder.add_test_result({"passed": True})
    builder.set_acceptance({"goal": "passed"})
    artifact = builder.build()
    gate = MergeGate()
    decision = gate.evaluate(artifact)
    assert decision.allowed_to_merge
    assert len(decision.blockers) == 0


def test_merge_gate_blocks_failed_tests() -> None:
    builder = ReviewArtifactBuilder("run-1")
    builder.add_test_result({"passed": False})
    artifact = builder.build()
    gate = MergeGate()
    decision = gate.evaluate(artifact)
    assert not decision.allowed_to_merge
    assert "tests_failed" in decision.blockers


def test_merge_gate_blocks_maintainability() -> None:
    builder = ReviewArtifactBuilder("run-1")
    artifact = builder.build()
    gate = MergeGate()
    decision = gate.evaluate(artifact, maintainability_blocked=True)
    assert not decision.allowed_to_merge
    assert "maintainability_blocked" in decision.blockers


def test_merge_gate_blocks_high_risk_no_reviewer() -> None:
    builder = ReviewArtifactBuilder("run-1")
    artifact = builder.build()
    gate = MergeGate()
    decision = gate.evaluate(artifact, high_risk=True)
    assert not decision.allowed_to_merge
    assert "high_risk_without_reviewer" in decision.blockers


def test_merge_gate_blocks_self_approval() -> None:
    builder = ReviewArtifactBuilder("run-1")
    builder.set_roles(reviewer="agent-1")
    artifact = builder.build()
    gate = MergeGate()
    decision = gate.evaluate(artifact, high_risk=True, producer_is_reviewer=True)
    assert not decision.allowed_to_merge
    assert "producer_self_approval" in decision.blockers


def test_merge_gate_requires_human_for_unknown() -> None:
    builder = ReviewArtifactBuilder("run-1")
    builder.set_acceptance({"performance": "unknown"})
    artifact = builder.build()
    gate = MergeGate()
    decision = gate.evaluate(artifact)
    assert decision.requires_human_approval


def test_artifact_json_serializable() -> None:
    builder = ReviewArtifactBuilder("run-1")
    builder.set_diff_summary({"files": 1})
    artifact = builder.build()
    data = artifact.model_dump(mode="json")
    assert "artifact_id" in data
    assert "decision" in data


def test_merge_decision_json_serializable() -> None:
    d = MergeGateDecision(review_artifact_id="art-1")
    data = d.model_dump(mode="json")
    assert "allowed_to_merge" in data
