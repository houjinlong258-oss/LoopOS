"""Provider gateway and multi-model scheduling contracts."""

from __future__ import annotations

from typing import Any, Literal, cast, get_args

from pydantic import BaseModel, Field, field_validator


ProviderCapability = Literal[
    "text",
    "coding",
    "vision",
    "tools",
    "embeddings",
    "reasoning",
    "audio",
    "video",
    "json_schema",
    "long_context",
    "streaming",
    "low_cost",
    "high_reliability",
    "local",
]
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
    "safety_judge",
    "policy_explainer",
]

_CAPABILITY_ALIASES = {
    "code": "coding",
    "tool_calling": "tools",
    "native_function_call": "tools",
    "function_calling": "tools",
    "local_only": "local",
}


def normalize_capability(value: str) -> ProviderCapability:
    canonical = _CAPABILITY_ALIASES.get(value.strip().lower(), value.strip().lower())
    if canonical not in set(get_args(ProviderCapability)):
        raise ValueError(f"unknown provider capability: {value}")
    return cast(ProviderCapability, canonical)


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
    local_only: bool = False

    @field_validator("id")
    @classmethod
    def id_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("provider id is required")
        return value

    @field_validator("capabilities", mode="before")
    @classmethod
    def normalize_capabilities(cls, value: Any) -> list[ProviderCapability]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("capabilities must be a list")
        return [normalize_capability(str(item)) for item in value]


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
