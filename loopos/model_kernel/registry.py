"""Static provider registry inspired by Hermes provider coverage."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from loopos.model_kernel.models import ProviderCapability, ProviderProfile, normalize_capability
from loopos.model_kernel.provider_loader import load_provider_profiles


_PROVIDER_IDS = [
    "openai",
    "openai-codex",
    "openrouter",
    "anthropic",
    "gemini",
    "deepseek",
    "kimi-coding",
    "minimax",
    "xai",
    "qwen-oauth",
    "alibaba",
    "huggingface",
    "bedrock",
    "azure-foundry",
    "ollama-cloud",
    "custom",
    "copilot",
    "copilot-acp",
    "nous",
    "novita",
    "nvidia",
    "xiaomi",
    "zai",
    "stepfun",
    "kilocode",
    "arcee",
    "gmi",
]


def _capabilities(provider_id: str) -> list[ProviderCapability]:
    coding = {"openai-codex", "deepseek", "kimi-coding", "qwen-oauth", "copilot", "kilocode"}
    vision = {"openai", "anthropic", "gemini", "openrouter", "minimax", "xai", "azure-foundry"}
    local = {"huggingface", "ollama-cloud"}
    caps: list[ProviderCapability] = ["text"]
    if provider_id in coding:
        caps.extend(["coding", "reasoning", "tools"])
    if provider_id in vision:
        caps.append("vision")
    if provider_id in local:
        caps.extend(["embeddings", "local", "coding", "reasoning"])
    return list(dict.fromkeys(caps))


class ProviderRegistry:
    def __init__(self, profiles: list[ProviderProfile] | None = None) -> None:
        selected = profiles
        if selected is None:
            profile_root = Path(__file__).resolve().parents[2] / "providers"
            selected = load_provider_profiles([profile_root]) if profile_root.exists() else []
            if not selected:
                selected = default_profiles()
        self._profiles = {profile.id: profile for profile in selected}

    def list(self) -> list[ProviderProfile]:
        return list(self._profiles.values())

    @classmethod
    def from_paths(
        cls,
        paths: Sequence[str | Path],
        *,
        include_defaults: bool = True,
    ) -> "ProviderRegistry":
        profiles = [*default_profiles()] if include_defaults else []
        loaded = load_provider_profiles(paths)
        by_id = {profile.id: profile for profile in profiles}
        by_id.update({profile.id: profile for profile in loaded})
        return cls(list(by_id.values()))

    def get(self, provider_id: str) -> ProviderProfile:
        if provider_id in self._profiles:
            return self._profiles[provider_id]
        for profile in self._profiles.values():
            if provider_id in profile.aliases:
                return profile
        raise KeyError(f"provider not found: {provider_id}")

    def route(self, required: Sequence[str], *, local_only: bool = False) -> ProviderProfile:
        required_set: set[ProviderCapability] = {normalize_capability(item) for item in required}
        candidates = [
            profile
            for profile in self._profiles.values()
            if required_set.issubset(set(profile.capabilities))
            and (not local_only or profile.local_only or "local" in profile.capabilities)
        ]
        if not candidates:
            raise KeyError(f"no provider supports capabilities: {required}")
        return sorted(candidates, key=lambda item: item.reliability_score, reverse=True)[0]


def default_profiles() -> list[ProviderProfile]:
    profiles: list[ProviderProfile] = []
    for provider_id in _PROVIDER_IDS:
        profiles.append(
            ProviderProfile(
                id=provider_id,
                aliases=[provider_id.replace("-", "_")],
                base_url=None,
                env_vars=[f"LOOPOS_{provider_id.replace('-', '_').upper()}_API_KEY"],
                capabilities=_capabilities(provider_id),
                default_models=[f"{provider_id}-default"],
                cost_class="unknown",
                latency_class="unknown",
                local_only=provider_id in {"huggingface", "ollama-cloud"},
                reliability_score=0.8 if provider_id in {"openai", "anthropic", "gemini"} else 0.6,
            )
        )
    return profiles
