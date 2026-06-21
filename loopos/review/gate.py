"""Review Artifact builder and Merge Gate evaluator."""

from __future__ import annotations

from typing import Any

from loopos.review.artifact import (
    MergeGateDecision,
    ReviewArtifact,
    ReviewChangeType,
    ReviewDecision,
    ReviewRiskLevel,
)


class ReviewArtifactBuilder:
    """Incrementally build a ReviewArtifact from run outputs."""

    def __init__(self, run_id: str, *, task_id: str | None = None) -> None:
        self._artifact = ReviewArtifact(run_id=run_id, task_id=task_id)

    def set_diff_summary(self, summary: dict[str, Any]) -> "ReviewArtifactBuilder":
        self._artifact.diff_summary = summary
        self._artifact.change_types = _derive_change_types(
            [str(path) for path in summary.get("changed_files", [])]
        )
        self._artifact.risk_level = _derive_risk_level(
            self._artifact.change_types,
            [str(flag) for flag in summary.get("risk_flags", [])],
        )
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

    def set_maintainability_evidence(
        self, report: dict[str, Any], gate: dict[str, Any]
    ) -> "ReviewArtifactBuilder":
        self._artifact.maintainability_report = report
        self._artifact.maintainability_report_id = str(report.get("report_id", "")) or None
        self._artifact.maintainability_gate = gate
        return self

    def set_trace_events(self, event_ids: list[str]) -> "ReviewArtifactBuilder":
        self._artifact.trace_event_ids = list(event_ids)
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
        required_actions: list[str] = []
        warnings: list[str] = []

        # Rule 1: Tests must pass
        tests_present = bool(artifact.tests_run)
        tests_passed = (
            all(t.get("passed", t.get("status") == "passed") for t in artifact.tests_run)
            if tests_present
            else False
        )

        if tests_present and not tests_passed:
            blockers.append("tests_failed")
        elif not tests_present:
            if _is_test_required_change(artifact.change_types):
                if _is_high_risk_change(artifact.change_types, artifact.risk_level, high_risk):
                    blockers.append("tests_required_for_high_risk_change")
                else:
                    reason_codes.append("tests_required_for_code_change")
                    required_actions.append("Add or cite deterministic tests for this code change.")
            else:
                warnings.append("no tests recorded for non-code or docs-only change")

        # Rule 2: Maintainability block
        embedded_maintainability_block = bool(
            artifact.maintainability_gate.get("blocks_merge", False)
        )
        if maintainability_blocked or embedded_maintainability_block:
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
        effective_high_risk = _is_high_risk_change(
            artifact.change_types,
            artifact.risk_level,
            high_risk,
        )

        if effective_high_risk and not artifact.reviewer_run_id:
            blockers.append("high_risk_without_reviewer")

        # Rule 8: Producer self-approval
        if producer_is_reviewer and effective_high_risk:
            blockers.append("producer_self_approval")

        # Decision
        if artifact.decision == "blocked":
            blockers.append("review_blocked")

        allowed = len(blockers) == 0 and len(required_actions) == 0
        if blockers:
            reason_codes.extend(blockers)

        return MergeGateDecision(
            review_artifact_id=artifact.artifact_id,
            allowed_to_merge=allowed,
            requires_human_approval=requires_human or bool(required_actions),
            reason_codes=reason_codes,
            blockers=blockers,
            required_actions=required_actions,
            warnings=warnings,
        )


def _derive_change_types(paths: list[str]) -> list[ReviewChangeType]:
    if not paths:
        return ["unknown"]
    types: set[ReviewChangeType] = set()
    for raw in paths:
        path = raw.replace("\\", "/").lower()
        name = path.rsplit("/", 1)[-1]
        if path.startswith("docs/") or name.endswith((".md", ".rst", ".txt")):
            types.add("docs")
        if "test" in path and path.endswith(".py"):
            types.add("tests")
        if path.startswith("loopos/kernel/"):
            types.add("kernel")
        if path.startswith("loopos/policy_os/") or path.startswith("policies/"):
            types.add("policy")
        if path.startswith("loopos/data_guard/") or "database" in path:
            types.add("data")
        if path.startswith("loopos/syscalls/"):
            types.add("syscall")
        if path.startswith("loopos/memory/"):
            types.add("memory")
        if path.startswith("loopos/registry/") or path.startswith("examples/plugins/"):
            types.add("plugin")
        if path.startswith("loopos/providers/") or path.startswith("providers/"):
            types.add("provider")
        if name in {"pyproject.toml", "setup.py"} or name.endswith((".yaml", ".yml", ".toml")):
            types.add("config")
        if path.endswith(".py") and "tests/" not in path:
            types.add("code")
    return sorted(types or {"unknown"})


def _derive_risk_level(
    change_types: list[ReviewChangeType], risk_flags: list[str]
) -> ReviewRiskLevel:
    if risk_flags:
        return "high"
    high_risk_types = {"kernel", "policy", "data", "syscall", "memory"}
    if high_risk_types.intersection(change_types):
        return "high"
    if "code" in change_types or "provider" in change_types or "plugin" in change_types:
        return "medium"
    return "low"


def _is_test_required_change(change_types: list[ReviewChangeType]) -> bool:
    return bool(set(change_types).intersection({"code", "kernel", "policy", "data", "syscall", "memory", "provider", "plugin", "config"}))


def _is_high_risk_change(
    change_types: list[ReviewChangeType],
    risk_level: ReviewRiskLevel,
    explicit_high_risk: bool,
) -> bool:
    return explicit_high_risk or risk_level in {"high", "blocked"} or bool(
        set(change_types).intersection({"kernel", "policy", "data", "syscall", "memory"})
    )
