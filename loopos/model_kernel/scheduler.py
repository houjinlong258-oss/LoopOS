"""Deterministic multi-model role scheduler."""

from __future__ import annotations

from loopos.model_kernel.models import ModelAssignment, ModelRole, ProviderCapability, VisionSummary
from loopos.model_kernel.registry import ProviderRegistry


_ROLE_CAPABILITIES: dict[ModelRole, list[ProviderCapability]] = {
    "primary_reasoner": ["text", "reasoning"],
    "coder": ["text", "coding"],
    "vision_companion": ["text", "vision"],
    "critic": ["text", "reasoning"],
    "verifier": ["text", "reasoning"],
    "aggregator": ["text"],
    "summarizer": ["text"],
    "policy_explainer": ["text", "reasoning"],
}


class MultiModelScheduler:
    def __init__(self, registry: ProviderRegistry | None = None) -> None:
        self.registry = registry or ProviderRegistry()

    def assign(
        self,
        role: ModelRole,
        *,
        required_capabilities: list[ProviderCapability] | None = None,
    ) -> ModelAssignment:
        required = required_capabilities or _ROLE_CAPABILITIES[role]
        profile = self.registry.route(required)
        return ModelAssignment(
            role=role,
            provider_id=profile.id,
            model=profile.default_models[0] if profile.default_models else None,
            capabilities=profile.capabilities,
            reason_code="capability_match",
        )

    def companion_for(
        self,
        primary: ModelAssignment,
        *,
        required_capability: ProviderCapability,
    ) -> ModelAssignment | None:
        if required_capability in primary.capabilities:
            return None
        if required_capability == "vision":
            return self.assign("vision_companion")
        return self.assign("aggregator", required_capabilities=["text", required_capability])

    def summarize_vision(self, source: str, summary: str) -> VisionSummary:
        companion = self.assign("vision_companion")
        return VisionSummary(source=source, summary=summary, provider_id=companion.provider_id)

