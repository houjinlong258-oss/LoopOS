"""Models for prompt / policy distillation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


SourceType = Literal[
    "agents_md", "claude_md", "codex_prompt",
    "project_doc", "public_guide", "user_rules",
]

PackStatus = Literal["draft", "active", "needs_review", "disabled"]


class PromptSource(BaseModel):
    """Reference to a source document for distillation."""
    source_id: str = Field(default_factory=lambda: str(uuid4()))
    path: str | None = None
    content_hash: str = ""
    source_sha256: str = ""
    hash_algorithm: str = "sha256"
    source_type: SourceType = "project_doc"
    license_note: str | None = None


class PromptSegment(BaseModel):
    """A classified section of a prompt source."""
    segment_id: str = Field(default_factory=lambda: str(uuid4()))
    source_id: str
    source_hash: str = ""
    segment_hash: str = ""
    category: Literal[
        "behavior", "planning", "interaction", "uncertainty",
        "rendering", "safety", "policy", "unknown",
    ] = "unknown"
    tags: list[str] = Field(default_factory=list)
    text: str = ""
    confidence: float = 0.0


class BehaviorPack(BaseModel):
    """Distilled behavior rules from prompt sources."""
    pack_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    tone_rules: list[str] = Field(default_factory=list)
    planning_rules: list[str] = Field(default_factory=list)
    interaction_rules: list[str] = Field(default_factory=list)
    uncertainty_rules: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    policy_conflicts: list[str] = Field(default_factory=list)
    activation_required: bool = True
    activation_steps: list[str] = Field(
        default_factory=lambda: [
            "review_distilled_rules",
            "resolve_policy_conflicts",
            "approve_activation",
        ]
    )
    status: PackStatus = "draft"


class RendererPack(BaseModel):
    """Distilled rendering/output formatting rules."""
    pack_id: str = Field(default_factory=lambda: str(uuid4()))
    markdown_rules: list[str] = Field(default_factory=list)
    cli_rules: list[str] = Field(default_factory=list)
    verbosity_rules: list[str] = Field(default_factory=list)
    examples: list[dict[str, Any]] = Field(default_factory=list)
    policy_conflicts: list[str] = Field(default_factory=list)
    activation_required: bool = True
    activation_steps: list[str] = Field(
        default_factory=lambda: [
            "review_renderer_rules",
            "confirm_no_source_text_copy",
            "approve_activation",
        ]
    )
    status: PackStatus = "draft"


class PolicyPackDraft(BaseModel):
    """Draft policy pack distilled from prompt analysis."""
    pack_id: str = Field(default_factory=lambda: str(uuid4()))
    source_id: str
    source_hash: str = ""
    proposed_rules: list[dict[str, Any]] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    policy_conflicts: list[str] = Field(default_factory=list)
    activation_workflow: list[str] = Field(
        default_factory=lambda: [
            "human_review_required",
            "policy_conflict_review",
            "activate_only_after_approval",
        ]
    )
    requires_human_review: bool = True
    created_at: datetime = Field(default_factory=_utc_now)


class DistillationAudit(BaseModel):
    """Audit record for a distillation run."""
    audit_id: str = Field(default_factory=lambda: str(uuid4()))
    source_id: str
    source_hash: str = ""
    segments_found: int = 0
    behavior_rules_extracted: int = 0
    renderer_rules_extracted: int = 0
    policy_rules_proposed: int = 0
    safety_conflicts: list[str] = Field(default_factory=list)
    policy_conflicts: list[str] = Field(default_factory=list)
    source_text_copied: bool = False
    copied_rule_ids: list[str] = Field(default_factory=list)
    activation_ready: bool = False
    created_at: datetime = Field(default_factory=_utc_now)
