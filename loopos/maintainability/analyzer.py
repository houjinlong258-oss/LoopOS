"""Maintainability analyzer — orchestrates rules and produces a scored report."""

from __future__ import annotations

from loopos.maintainability.architecture import ArchitectureBoundaryRules
from loopos.maintainability.models import (
    CodeChangeSummary,
    MaintainabilityFinding,
    MaintainabilityReport,
    Recommendation,
    RiskLevel,
)
from loopos.maintainability.rules import (
    FileContentMap,
    check_broad_exception,
    check_bypass_patterns,
    check_complexity,
    check_hardcoded_values,
    check_hidden_global_state,
    check_large_diff,
    check_missing_tests,
    check_unrelated_changes,
)
from loopos.maintainability.test_quality import TestQualityRules

# ---------------------------------------------------------------------------
# Scoring weights per category
# ---------------------------------------------------------------------------
_DEDUCTIONS: dict[str, dict[str, int]] = {
    "large_diff": {"warning": 10, "error": 25},
    "unrelated_change": {"warning": 15, "error": 15},
    "missing_test": {"warning": 15, "error": 25},
    "weak_test": {"warning": 5, "error": 10},
    "complexity": {"warning": 5, "error": 15},
    "duplication": {"warning": 5, "error": 15},
    "broad_exception": {"warning": 5, "error": 10},
    "hardcoded_value": {"warning": 5, "error": 15},
    "hidden_global_state": {"warning": 5, "error": 10},
    "missing_docs": {"warning": 3, "error": 8},
    "naming": {"warning": 2, "error": 5},
    "dependency_risk": {"warning": 5, "error": 10},
    "module_boundary": {"warning": 5, "error": 15},
    "dead_code": {"warning": 3, "error": 5},
    "over_abstraction": {"warning": 3, "error": 8},
    "under_abstraction": {"warning": 3, "error": 8},
    "migration_risk": {"warning": 5, "error": 10},
    "error_swallowing": {"warning": 5, "error": 10},
}

# Blockers automatically set score to 0 and block
_BLOCKER_CATEGORIES = {
    "policy_bypass",
    "syscall_bypass",
    "data_guard_bypass",
    "memory_bypass",
    "trace_bypass",
}


class MaintainabilityAnalyzer:
    """Run all rules and produce a MaintainabilityReport."""

    def __init__(
        self,
        *,
        architecture: ArchitectureBoundaryRules | None = None,
        test_quality: TestQualityRules | None = None,
    ) -> None:
        self.architecture = architecture or ArchitectureBoundaryRules()
        self.test_quality = test_quality or TestQualityRules()

    def analyze(
        self,
        summary: CodeChangeSummary,
        files: FileContentMap | None = None,
    ) -> MaintainabilityReport:
        files = files or {}
        findings: list[MaintainabilityFinding] = []

        # Summary-level rules
        findings.extend(check_large_diff(summary))
        findings.extend(check_missing_tests(summary))
        findings.extend(check_unrelated_changes(summary))

        # Content-level rules
        if files:
            findings.extend(check_broad_exception(files))
            findings.extend(check_hardcoded_values(files))
            findings.extend(check_hidden_global_state(files))
            findings.extend(check_complexity(files))
            findings.extend(check_bypass_patterns(files))
            findings.extend(self.architecture.check_boundary_crossings(summary, files))
            findings.extend(self.test_quality.check(summary, files))

        # Score
        score, risk_level, recommendation = self._compute_score(findings)

        # Risk breakdown
        duplication_risk = self._category_risk(findings, {"duplication"})
        complexity_risk = self._category_risk(findings, {"complexity"})
        boundary_risk = self._category_risk(findings, {"module_boundary", "unrelated_change"})
        test_quality_risk = self._category_risk(findings, {"missing_test", "weak_test"})
        documentation_risk = self._category_risk(findings, {"missing_docs"})
        policy_bypass_risk = self._category_risk(findings, _BLOCKER_CATEGORIES)

        report_summary = self._build_summary(summary, findings, score, recommendation)

        return MaintainabilityReport(
            run_id=summary.run_id,
            changed_files=summary.changed_files,
            score=score,
            risk_level=risk_level,
            findings=findings,
            duplication_risk=duplication_risk,
            complexity_risk=complexity_risk,
            boundary_risk=boundary_risk,
            test_quality_risk=test_quality_risk,
            documentation_risk=documentation_risk,
            policy_bypass_risk=policy_bypass_risk,
            recommendation=recommendation,
            summary=report_summary,
        )

    def _compute_score(
        self, findings: list[MaintainabilityFinding]
    ) -> tuple[float, RiskLevel, Recommendation]:
        score = 100.0
        has_blocker = False

        for finding in findings:
            if finding.severity == "blocker":
                has_blocker = True
                continue
            deduction = _DEDUCTIONS.get(finding.category, {}).get(finding.severity, 5)
            score -= deduction

        if has_blocker:
            score = 0.0

        score = max(0.0, min(100.0, score))

        if has_blocker or score < 40:
            return score, "blocked", "block"
        if score < 60:
            return score, "high", "refactor_required"
        if score < 75:
            return score, "medium", "request_changes"
        if score < 90:
            return score, "low", "approve_with_warnings"
        return score, "low", "approve"

    def _category_risk(
        self,
        findings: list[MaintainabilityFinding],
        categories: set[str],
    ) -> float:
        matched = [f for f in findings if f.category in categories]
        if not matched:
            return 0.0
        severity_score = {
            "info": 0.1,
            "warning": 0.3,
            "error": 0.6,
            "blocker": 1.0,
        }
        return min(1.0, sum(severity_score.get(f.severity, 0.1) for f in matched))

    def _build_summary(
        self,
        summary: CodeChangeSummary,
        findings: list[MaintainabilityFinding],
        score: float,
        recommendation: Recommendation,
    ) -> str:
        parts: list[str] = []
        parts.append(f"Score: {score:.0f}/100 — {recommendation.replace('_', ' ').title()}")
        parts.append(f"Files: {len(summary.changed_files)} changed")
        parts.append(f"Lines: +{summary.added_lines} / -{summary.removed_lines}")

        blockers = [f for f in findings if f.severity == "blocker"]
        errors = [f for f in findings if f.severity == "error"]
        warnings = [f for f in findings if f.severity == "warning"]

        if blockers:
            parts.append(f"Blockers: {len(blockers)}")
        if errors:
            parts.append(f"Errors: {len(errors)}")
        if warnings:
            parts.append(f"Warnings: {len(warnings)}")

        return " | ".join(parts)
