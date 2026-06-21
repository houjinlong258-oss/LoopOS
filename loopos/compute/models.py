"""Hybrid compute routing contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ComputeMode = Literal["privacy-local", "hybrid", "cloud-power"]


class ComputeConfig(BaseModel):
    schema_version: str = "1.0"
    mode: ComputeMode = "privacy-local"


class ComputeDecision(BaseModel):
    mode: ComputeMode
    local_only: bool
    cloud_allowed: bool
    requires_consent: bool = False
    reason_codes: list[str] = Field(default_factory=list)
