"""Typed models for the Fusion Router.

FusionRequest  — what task needs multi-model attention.
FusionPanel    — which models are selected and why.
JudgeReport    — synthesis of multi-model outputs.
FusionResult   — final fused output.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


TaskType = Literal[
    "research", "coding", "planning", "review",
    "debugging", "multimodal", "policy", "unknown",
]

BudgetLevel = Literal["cheap", "balanced", "best"]
LatencyPref = Literal["fast", "balanced", "slow"]
PrivacyMode = Literal["local_only", "hybrid", "cloud_allowed"]
RiskLevel = Literal["low", "medium", "high"]
CostClass = Literal["low", "medium", "high"]


class FusionRequest(BaseModel):
    """Input to the fusion router."""
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    task_type: TaskType = "unknown"
    prompt: str
    context_refs: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = "medium"
    budget: BudgetLevel = "balanced"
    latency_preference: LatencyPref = "balanced"
    privacy_mode: PrivacyMode = "hybrid"
    candidate_models: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)


class FusionPanel(BaseModel):
    """Selected models for a fusion task."""
    panel_id: str = Field(default_factory=lambda: str(uuid4()))
    request_id: str
    models: list[str] = Field(default_factory=list)
    judge_model: str = ""
    aggregator_model: str | None = None
    routing_reason: list[str] = Field(default_factory=list)
    estimated_cost_class: CostClass = "medium"


class ModelResponse(BaseModel):
    """Raw response from one model in the panel."""
    model_id: str
    content: str
    latency_ms: int = 0
    token_count: int = 0


class JudgeReport(BaseModel):
    """Synthesis report comparing multi-model outputs."""
    judge_report_id: str = Field(default_factory=lambda: str(uuid4()))
    request_id: str
    consensus: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    coverage_gaps: list[str] = Field(default_factory=list)
    unique_insights: list[str] = Field(default_factory=list)
    blind_spots: list[str] = Field(default_factory=list)
    model_strengths: dict[str, list[str]] = Field(default_factory=dict)
    model_weaknesses: dict[str, list[str]] = Field(default_factory=dict)
    confidence: float = 0.0
    recommended_source_ids: list[str] = Field(default_factory=list)


class FusionResult(BaseModel):
    """Final fused output."""
    fusion_result_id: str = Field(default_factory=lambda: str(uuid4()))
    request_id: str
    final_content: str = ""
    judge_report: JudgeReport
    contributing_models: list[str] = Field(default_factory=list)
    cost_estimate: float | None = None
    latency_ms: int | None = None
    trace_event_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)
