"""Typed models for the Maintainability Kernel.

CodeChangeSummary  — what changed.
MaintainabilityFinding  — one concern.
MaintainabilityReport — scored assessment.
MaintainabilityGateDecision — pass/block.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

FindingCategory = Literal[
    "large_diff",
    "unrelated_change",
    "duplication",
    "complexity",
    "module_boundary",
    "missing_test",
    "weak_test",
    "missing_docs",
    "hardcoded_value",
    "hidden_global_state",
    "broad_exception",
    "error_swallowing",
    "policy_bypass",
    "syscall_bypass",
    "data_guard_bypass",
    "memory_bypass",
    "trace_bypass",
    "dead_code",
    "over_abstraction",
    "under_abstraction",
    "naming",
    "dependency_risk",
    "migration_risk",
    "empty_diff",
    "invalid_diff_format",
    "diff_without_file_header",
    "unparsed_added_lines",
    "risk_content_in_unparsed_diff",
]

FindingSeverity = Literal["info", "warning", "error", "blocker"]

RiskLevel = Literal["low", "medium", "high", "blocked"]
DiffParseStatus = Literal["parsed", "empty", "non_diff", "partial", "invalid"]

Recommendation = Literal[
    "approve",
    "approve_with_warnings",
    "request_changes",
    "refactor_required",
    "block",
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CodeChangeSummary(BaseModel):
    """Structured summary of what a code change contains."""

    summary_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str | None = None
    base_ref: str | None = None
    head_ref: str | None = None
    parse_status: DiffParseStatus = "parsed"
    parse_warnings: list[str] = Field(default_factory=list)
    changed_files: list[str] = Field(default_factory=list)
    added_lines: int = 0
    removed_lines: int = 0
    modified_lines: int = 0
    modified_symbols: list[str] = Field(default_factory=list)
    new_dependencies: list[str] = Field(default_factory=list)
    new_public_apis: list[str] = Field(default_factory=list)
    deleted_public_apis: list[str] = Field(default_factory=list)
    test_files_changed: list[str] = Field(default_factory=list)
    docs_changed: list[str] = Field(default_factory=list)
    config_files_changed: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class MaintainabilityFinding(BaseModel):
    """A single maintainability concern discovered by the analyzer."""

    finding_id: str = Field(default_factory=lambda: str(uuid4()))
    category: FindingCategory
    severity: FindingSeverity
    file: str | None = None
    line: int | None = None
    symbol: str | None = None
    message: str
    suggested_fix: str | None = None
    evidence: list[str] = Field(default_factory=list)


class MaintainabilityReport(BaseModel):
    """Scored maintainability assessment for a code change."""

    report_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str | None = None
    step: int | None = None
    parse_status: DiffParseStatus = "parsed"
    changed_files: list[str] = Field(default_factory=list)
    score: float = 100.0
    risk_level: RiskLevel = "low"
    findings: list[MaintainabilityFinding] = Field(default_factory=list)
    duplication_risk: float = 0.0
    complexity_risk: float = 0.0
    boundary_risk: float = 0.0
    test_quality_risk: float = 0.0
    documentation_risk: float = 0.0
    policy_bypass_risk: float = 0.0
    recommendation: Recommendation = "approve"
    summary: str = ""
    created_at: datetime = Field(default_factory=_utc_now)


class MaintainabilityGateDecision(BaseModel):
    """Gate decision determining whether a change may proceed."""

    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    report_id: str
    allowed_to_continue: bool = True
    requires_refactor: bool = False
    requires_human_review: bool = False
    blocks_merge: bool = False
    reason_codes: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
