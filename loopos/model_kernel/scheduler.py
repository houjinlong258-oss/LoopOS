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
    "safety_judge": ["text", "reasoning"],
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
        local_only: bool = False,
    ) -> ModelAssignment:
        required = required_capabilities or _ROLE_CAPABILITIES[role]
        profile = self.registry.route(required, local_only=local_only)
        return ModelAssignment(
            role=role,
            provider_id=profile.id,
            model=profile.default_models[0] if profile.default_models else None,
            capabilities=profile.capabilities,
            reason_code="privacy_local" if local_only else "capability_match",
        )

    def companion_for(
        self,
        primary: ModelAssignment,
        *,
        required_capability: ProviderCapability,
        local_only: bool = False,
    ) -> ModelAssignment | None:
        if required_capability in primary.capabilities:
            return None
        if required_capability == "vision":
            return self.assign("vision_companion", local_only=local_only)
        return self.assign(
            "aggregator",
            required_capabilities=["text", required_capability],
            local_only=local_only,
        )

    def route_task(
        self,
        *,
        task: str,
        input_kind: str | None = None,
        secret: bool = False,
    ) -> list[ModelAssignment]:
        normalized_task = task.strip().lower()
        if normalized_task in {"coding", "code"}:
            primary = self.assign("coder", local_only=secret)
        elif normalized_task in {"verify", "verification"}:
            primary = self.assign("verifier", local_only=secret)
        else:
            primary = self.assign("primary_reasoner", local_only=secret)
        assignments = [primary]
        if input_kind and input_kind.strip().lower() in {"image", "vision", "screenshot"}:
            companion = self.companion_for(primary, required_capability="vision", local_only=secret)
            if companion is not None:
                assignments.append(companion)
        return assignments

    def summarize_vision(self, source: str, summary: str) -> VisionSummary:
        companion = self.assign("vision_companion")
        return VisionSummary(source=source, summary=summary, provider_id=companion.provider_id)
