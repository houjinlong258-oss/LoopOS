"""Token economy models for Project Training Runtime."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class TokenBudgetRecord(BaseModel):
    """Token accounting for one loop iteration."""

    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(default_factory=lambda: f"tok_{uuid4().hex[:10]}")
    run_id: str
    iteration_index: int = 0
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    context_tokens: int = Field(default=0, ge=0)
    saved_tokens: int = Field(default=0, ge=0)
    budget: int = Field(default=0, ge=0)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + self.context_tokens

    @property
    def over_budget(self) -> bool:
        return self.budget > 0 and self.total_tokens > self.budget


class TokenWasteFinding(BaseModel):
    """A token waste signal that can feed Mad Dog / Fusion."""

    model_config = ConfigDict(extra="forbid")

    reason: str
    wasted_tokens_estimate: int = Field(default=0, ge=0)
    recommended_fix: str = ""


__all__ = ["TokenBudgetRecord", "TokenWasteFinding"]
