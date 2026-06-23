"""Provider budget guard."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BudgetDecision(BaseModel):
    """Structured result of a budget check."""

    model_config = ConfigDict(extra="forbid")

    allowed: bool
    reason_codes: list[str] = Field(default_factory=list)
    used_usd: float = 0.0
    requested_estimate_usd: float = 0.0
    max_usd: float = 0.0
    requires_approval: bool = False


class ProviderBudget(BaseModel):
    """Mutable budget tracker for a sequence of provider calls."""

    model_config = ConfigDict(extra="forbid")

    max_usd: float = Field(default=0.0, ge=0.0)
    used_usd: float = Field(default=0.0, ge=0.0)
    max_requests: int | None = Field(default=None, ge=0)
    used_requests: int = Field(default=0, ge=0)
    require_approval_above_usd: float = Field(default=1.0, ge=0.0)

    def check(self, estimated_cost_usd: float, *, approved: bool = False) -> BudgetDecision:
        """Return a :class:`BudgetDecision` for a prospective call."""
        reasons: list[str] = []
        prospective = self.used_usd + max(0.0, estimated_cost_usd)

        if self.max_requests is not None and self.used_requests >= self.max_requests:
            reasons.append("provider_request_count_exceeded")

        if self.max_usd > 0.0 and prospective > self.max_usd:
            reasons.append("provider_budget_exceeded")

        requires_approval = estimated_cost_usd > self.require_approval_above_usd and not approved
        if requires_approval:
            reasons.append("provider_call_requires_approval")

        allowed = not reasons
        return BudgetDecision(
            allowed=allowed,
            reason_codes=reasons,
            used_usd=self.used_usd,
            requested_estimate_usd=estimated_cost_usd,
            max_usd=self.max_usd,
            requires_approval=requires_approval,
        )

    def commit(self, actual_cost_usd: float) -> None:
        """Record a completed call's actual cost."""
        self.used_usd += max(0.0, actual_cost_usd)
        self.used_requests += 1


__all__ = ["ProviderBudget", "BudgetDecision"]
