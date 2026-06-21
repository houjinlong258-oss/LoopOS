"""Review Artifact and Merge Gate models.

ReviewArtifact — structured reviewable record of an agent-produced change.
MergeGateDecision — whether a change may be merged.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


AcceptanceStatus = Literal["passed", "failed", "unknown"]
ReviewDecision = Literal["approve", "request_changes", "reject", "blocked"]
MergeDecision = Literal["merge_allowed", "merge_blocked"]


class ReviewArtifact(BaseModel):
    """Structured review artifact for an agent-produced code change."""

    artifact_id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str | None = None
    run_id: str
    producer_run_id: str | None = None
    verifier_run_id: str | None = None
    reviewer_run_id: str | None = None
    diff_summary: dict[str, Any] = Field(default_factory=dict)
    tests_run: list[dict[str, Any]] = Field(default_factory=list)
    policy_checks: list[dict[str, Any]] = Field(default_factory=list)
    data_guard_checks: list[dict[str, Any]] = Field(default_factory=list)
    maintainability_report_id: str | None = None
    acceptance_status: dict[str, AcceptanceStatus] = Field(default_factory=dict)
    findings: list[str] = Field(default_factory=list)
    required_changes: list[str] = Field(default_factory=list)
    decision: ReviewDecision = "approve"
    created_at: datetime = Field(default_factory=_utc_now)


class MergeGateDecision(BaseModel):
    """Whether a reviewed change may be merged."""

    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    review_artifact_id: str
    allowed_to_merge: bool = True
    requires_human_approval: bool = False
    reason_codes: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
