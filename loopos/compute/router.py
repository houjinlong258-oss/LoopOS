"""Deterministic privacy-aware compute router."""

from __future__ import annotations

import json
from pathlib import Path

from loopos.compute.models import ComputeConfig, ComputeDecision, ComputeMode


class ComputeModeStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> ComputeConfig:
        if not self.path.exists():
            return ComputeConfig()
        return ComputeConfig.model_validate_json(self.path.read_text(encoding="utf-8"))

    def set(self, mode: ComputeMode) -> ComputeConfig:
        config = ComputeConfig(mode=mode)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(config.model_dump(mode="json"), indent=2), encoding="utf-8")
        return config


class ComputeRouter:
    def decide(
        self,
        mode: ComputeMode,
        *,
        private_data: bool = False,
        sanitized: bool = False,
        cloud_consent: bool = False,
    ) -> ComputeDecision:
        if private_data:
            return ComputeDecision(
                mode=mode,
                local_only=True,
                cloud_allowed=False,
                reason_codes=["compute.private_data_local_only"],
            )
        if mode == "privacy-local":
            return ComputeDecision(
                mode=mode,
                local_only=True,
                cloud_allowed=False,
                reason_codes=["compute.privacy_local"],
            )
        if mode == "hybrid":
            return ComputeDecision(
                mode=mode,
                local_only=not sanitized,
                cloud_allowed=sanitized,
                reason_codes=["compute.hybrid_sanitized" if sanitized else "compute.hybrid_requires_sanitization"],
            )
        return ComputeDecision(
            mode=mode,
            local_only=not cloud_consent,
            cloud_allowed=cloud_consent,
            requires_consent=not cloud_consent,
            reason_codes=["compute.cloud_consent_recorded" if cloud_consent else "compute.cloud_consent_required"],
        )
