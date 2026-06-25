"""Production readiness models."""

from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


ProductionReadinessStatus = Literal["ready", "not_ready", "blocked"]


class ProductionReadinessReport(BaseModel):
    """Deployability report consumed by delivery decisions."""

    model_config = ConfigDict(extra="forbid")

    report_id: str = Field(default_factory=lambda: f"prod_{uuid4().hex[:10]}")
    status: ProductionReadinessStatus = "not_ready"
    evidence: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    demo_only_signals: list[str] = Field(default_factory=list)
    delivery_reference: str = ""


__all__ = ["ProductionReadinessReport", "ProductionReadinessStatus"]
