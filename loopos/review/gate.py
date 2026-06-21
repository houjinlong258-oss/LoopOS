"""Review Artifact builder and Merge Gate evaluator."""

from __future__ import annotations

from typing import Any

from loopos.review.artifact import (
    MergeGateDecision,
    ReviewArtifact,
    ReviewDecision,
)


class ReviewArtifactBuilder:
    """Incrementally build a ReviewArtifact from run outputs."""

    def __init__(self, run_id: str, *, task_id: str | None = None) -> None:
        self._artifact = ReviewArtifact(run_id=run_id, task_id=task_id)

    def set_diff_summary(self, summary: dict[str, Any]) -> "ReviewArtifactBuilder":
        self._artifact.diff_summary = summary
        return self

    def add_test_result(self, result: dict[str, Any]) -> "ReviewArtifactBuilder":
        self._artifact.tests_run.append(result)
        return self

    def add_policy_check(self, check: dict[str, Any]) -> "ReviewArtifactBuilder":
        self._artifact.policy_checks.append(check)
        return self

    def add_data_guard_check(self, check: dict[str, Any]) -> "ReviewArtifactBuilder":
        self._artifact.data_guard_checks.append(check)
        return self

    def set_maintainability_report(self, report_id: str) -> "ReviewArtifactBuilder":
        self._artifact.maintainability_report_id = report_id
        return self

    def set_acceptance(self, criteria: dict[str, str]) -> "ReviewArtifactBuilder":
        self._artifact.acceptance_status = criteria  # type: ignore[assignment]
        return self

    def add_finding(self, finding: str) -> "ReviewArtifactBuilder":
        self._artifact.findings.append(finding)
        return self

    def add_required_change(self, change: str) -> "ReviewArtifactBuilder":
        self._artifact.required_changes.append(change)
        return self

    def set_roles(
        self,
        *,
        producer: str | None = None,
        verifier: str | None = None,
        reviewer: str | None = None,
    ) -> "ReviewArtifactBuilder":
        self._artifact.producer_run_id = producer
        self._artifact.verifier_run_id = verifier
        self._artifact.reviewer_run_id = reviewer
        return self

    def build(self) -> ReviewArtifact:
        """Finalize and return the ReviewArtifact."""
        self._artifact.decision = self._determine_decision()
        return self._artifact

    def _determine_decision(self) -> ReviewDecision:
        # Any blocker in policy checks
        for check in self._artifact.policy_checks:
            if check.get("severity") == "blocker" or not check.get("allowed", True):
                return "blocked"

        # Failed acceptance criteria
        for criterion, status in self._artifact.acceptance_status.items():
            if status == "failed":
                return "reject"

        # Required changes pending
        if self._artifact.required_changes:
            return "request_changes"

        # Findings without required changes
        if self._artifact.findings:
            return "request_changes"

        return "approve"


class MergeGate:
    """Evaluate a ReviewArtifact and decide whether merging is allowed."""

    def evaluate(
        self,
        artifact: ReviewArtifact,
        *,
        maintainability_blocked: bool = False,
        high_risk: bool = False,
        producer_is_reviewer: bool = False,
    ) -> MergeGateDecision:
        blockers: list[str] = []
        reason_codes: list[str] = []

        # Rule 1: Tests must pass
        tests_passed = all(
            t.get("passed", t.get("status") == "passed")
            for t in artifact.tests_run
        ) if artifact.tests_run else True  # No tests is not itself a blocker here

        if not tests_passed:
            blockers.append("tests_failed")

        # Rule 2: Maintainability block
        if maintainability_blocked:
            blockers.append("maintainability_blocked")

        # Rule 3: Policy violations
        for check in artifact.policy_checks:
            if not check.get("allowed", True):
                blockers.append(f"policy_violation:{check.get('rule', 'unknown')}")

        # Rule 4: Data guard failures
        for check in artifact.data_guard_checks:
            if not check.get("passed", True):
                blockers.append(f"data_guard_failure:{check.get('target', 'unknown')}")

        # Rule 5: Failed acceptance criteria
        for criterion, status in artifact.acceptance_status.items():
            if status == "failed":
                blockers.append(f"acceptance_failed:{criterion}")

        # Rule 6: Unknown acceptance blocks auto-approval
        has_unknown = any(
            s == "unknown" for s in artifact.acceptance_status.values()
        )
        requires_human = has_unknown

        # Rule 7: High-risk without reviewer
        if high_risk and not artifact.reviewer_run_id:
            blockers.append("high_risk_without_reviewer")

        # Rule 8: Producer self-approval
        if producer_is_reviewer and high_risk:
            blockers.append("producer_self_approval")

        # Decision
        if artifact.decision == "blocked":
            blockers.append("review_blocked")

        allowed = len(blockers) == 0
        if blockers:
            reason_codes.extend(blockers)

        return MergeGateDecision(
            review_artifact_id=artifact.artifact_id,
            allowed_to_merge=allowed,
            requires_human_approval=requires_human,
            reason_codes=reason_codes,
            blockers=blockers,
        )
