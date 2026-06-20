"""Provider gateway and multi-model scheduling contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


ProviderCapability = Literal["text", "coding", "vision", "tools", "embeddings", "reasoning"]
ProviderCostClass = Literal["low", "medium", "high", "local", "unknown"]
ProviderLatencyClass = Literal["low", "medium", "high", "unknown"]
ModelRole = Literal[
    "primary_reasoner",
    "coder",
    "vision_companion",
    "critic",
    "verifier",
    "aggregator",
    "summarizer",
    "policy_explainer",
]


class ProviderProfile(BaseModel):
    id: str
    aliases: list[str] = Field(default_factory=list)
    base_url: str | None = None
    auth_type: str = "env"
    api_mode: str = "openai-compatible"
    env_vars: list[str] = Field(default_factory=list)
    capabilities: list[ProviderCapability] = Field(default_factory=list)
    default_models: list[str] = Field(default_factory=list)
    cost_class: ProviderCostClass = "unknown"
    latency_class: ProviderLatencyClass = "unknown"
    reliability_score: float = Field(default=0.5, ge=0.0, le=1.0)

    @field_validator("id")
    @classmethod
    def id_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("provider id is required")
        return value


class ModelAssignment(BaseModel):
    role: ModelRole
    provider_id: str
    model: str | None = None
    capabilities: list[ProviderCapability] = Field(default_factory=list)
    reason_code: str


class VisionSummary(BaseModel):
    source: str
    summary: str
    provider_id: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)

