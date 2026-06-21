"""Fusion router — selects model panels based on task, budget, privacy, and risk.

v0.5: Optionally backed by the real ProviderRegistry so that panel
selection reflects actual provider capabilities. Privacy mode is
enforced against the provider profile's ``local_only`` flag, blocking
cloud models from receiving sensitive context.
"""

from __future__ import annotations

from typing import Literal, TypedDict

from loopos.fusion.models import FusionPanel, FusionRequest
from loopos.model_kernel.models import ProviderProfile
from loopos.model_kernel.registry import ProviderRegistry


class _ModelSpec(TypedDict):
    capability: list[str]
    cost: Literal["low", "medium", "high"]
    local: bool


# Mock model registry used when no ProviderRegistry is supplied.
_MOCK_MODELS: dict[str, _ModelSpec] = {
    "local-small": {"capability": ["coding", "planning"], "cost": "low", "local": True},
    "local-medium": {"capability": ["coding", "planning", "review"], "cost": "medium", "local": True},
    "cloud-fast": {"capability": ["coding", "research"], "cost": "low", "local": False},
    "cloud-strong": {"capability": ["coding", "planning", "review", "debugging", "research"], "cost": "medium", "local": False},
    "cloud-best": {"capability": ["coding", "planning", "review", "debugging", "research", "multimodal"], "cost": "high", "local": False},
}


class FusionRouter:
    """Route a FusionRequest to an appropriate model panel."""

    def __init__(self, *, registry: ProviderRegistry | None = None) -> None:
        self.registry = registry

    def plan(self, request: FusionRequest) -> FusionPanel:
        """Select models for the fusion panel."""
        eligible = self._filter_models(request)
        panel_size = self._panel_size(request)
        selected = eligible[:panel_size]

        # Always add a judge
        judge = selected[0] if selected else "local-small"

        # High-risk tasks include a verifier
        routing_reason: list[str] = []
        if request.risk_level == "high":
            routing_reason.append("high_risk_includes_verifier")
            if len(selected) < 2 and len(eligible) >= 2:
                selected = eligible[:2]

        if request.task_type == "review":
            routing_reason.append("review_task_includes_critic")

        routing_reason.append(f"budget:{request.budget}")
        routing_reason.append(f"privacy:{request.privacy_mode}")

        if self.registry is not None:
            routing_reason.append("source:provider_registry")
        else:
            routing_reason.append("source:mock_registry")

        cost_class = "low" if request.budget == "cheap" else (
            "high" if request.budget == "best" else "medium"
        )

        return FusionPanel(
            request_id=request.request_id,
            models=[m for m in selected],
            judge_model=judge,
            routing_reason=routing_reason,
            estimated_cost_class=cost_class,
        )

    def _filter_models(self, request: FusionRequest) -> list[str]:
        """Filter models by privacy, capability, and budget."""
        if self.registry is not None:
            return self._filter_provider_models(request)
        return self._filter_mock_models(request)

    def _filter_mock_models(self, request: FusionRequest) -> list[str]:
        eligible: list[str] = []
        for name, info in _MOCK_MODELS.items():
            # Privacy filter
            if request.privacy_mode == "local_only" and not info.get("local", False):
                continue
            # Capability filter
            if request.required_capabilities:
                model_caps = info.get("capability", [])
                if not any(cap in model_caps for cap in request.required_capabilities):
                    continue
            # Candidate filter
            if request.candidate_models and name not in request.candidate_models:
                continue
            eligible.append(name)

        # Sort by cost preference
        cost_order = {"low": 0, "medium": 1, "high": 2}
        if request.budget == "cheap":
            eligible.sort(key=lambda m: cost_order.get(_MOCK_MODELS[m].get("cost", "medium"), 1))
        elif request.budget == "best":
            eligible.sort(key=lambda m: cost_order.get(_MOCK_MODELS[m].get("cost", "medium"), 1), reverse=True)

        return eligible

    def _filter_provider_models(self, request: FusionRequest) -> list[str]:
        """Filter using real ProviderProfile records from the ProviderRegistry."""
        eligible: list[ProviderProfile] = []
        local_only_required = request.privacy_mode == "local_only"
        for profile in self.registry.list() if self.registry else []:
            # Privacy filter: cloud_allowed allows anything; hybrid allows
            # cloud only if no sensitive context; local_only blocks cloud.
            if local_only_required and not profile.local_only and "local" not in profile.capabilities:
                continue
            # Capability filter
            if request.required_capabilities:
                profile_caps = set(profile.capabilities)
                required_caps = {str(c) for c in request.required_capabilities}
                if not required_caps.issubset(profile_caps):
                    continue
            # Candidate filter
            if request.candidate_models and profile.id not in request.candidate_models:
                continue
            eligible.append(profile)

        # Sort by reliability then cost preference
        cost_order = {"low": 0, "medium": 1, "high": 2, "local": 0, "unknown": 1}
        if request.budget == "cheap":
            eligible.sort(
                key=lambda p: (cost_order.get(p.cost_class, 1), -p.reliability_score)
            )
        elif request.budget == "best":
            eligible.sort(
                key=lambda p: (-p.reliability_score, -cost_order.get(p.cost_class, 1))
            )
        else:
            eligible.sort(key=lambda p: -p.reliability_score)
        return [profile.id for profile in eligible]

    def _panel_size(self, request: FusionRequest) -> int:
        """Determine how many models to include."""
        if request.budget == "cheap":
            return 1
        if request.budget == "best":
            return 3
        return 2
