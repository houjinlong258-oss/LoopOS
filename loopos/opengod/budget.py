"""OpenGod budget guard.

The :class:`OpenGodBudgetGuard` is a defensive layer that **refuses**
to authorise a strategic decision that would lead to live provider
spend beyond a configured ceiling. OpenGod does not itself spend
money — that responsibility lives in the provider runtime — but it
must not produce a verdict that would ask the runtime to exceed
the budget.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from loopos.opengod.models import OpenGodContext, OpenGodDecision, OpenGodDecisionKind


# Decision kinds that imply live provider spend.
_LIVE_SPEND_KINDS: frozenset[OpenGodDecisionKind] = frozenset(
    {"fusion_pair", "fusion_committee", "mad_dog", "adapter_agent"}
)


class BudgetAssessment(BaseModel):
    """Result of a budget guard check."""

    model_config = ConfigDict(extra="forbid")

    allowed: bool
    decision: OpenGodDecision
    reason_codes: list[str] = Field(default_factory=list)
    would_spend_usd: float = 0.0
    max_usd: float = 0.0
    projected_used_usd: float = 0.0


class OpenGodBudgetGuard:
    """Static budget guard for OpenGod decisions."""

    def __init__(
        self,
        *,
        max_usd: float = 1.0,
        reserve_usd: float = 0.10,
        cost_per_live_call_usd: float = 0.05,
    ) -> None:
        self.max_usd = max(0.0, float(max_usd))
        self.reserve_usd = max(0.0, float(reserve_usd))
        self.cost_per_live_call_usd = max(0.0, float(cost_per_live_call_usd))

    def assess(
        self,
        context: OpenGodContext,
        decision: OpenGodDecision,
        *,
        estimated_live_calls: int = 1,
    ) -> BudgetAssessment:
        """Decide whether the decision is allowed under the budget."""
        if decision.kind not in _LIVE_SPEND_KINDS:
            return BudgetAssessment(
                allowed=True,
                decision=decision,
                reason_codes=["no_live_spend"],
            )
        would_spend = max(0, int(estimated_live_calls)) * self.cost_per_live_call_usd
        projected = context.budget_used_usd + would_spend
        ceiling = self.max_usd - self.reserve_usd
        reasons: list[str] = []
        # Block whenever the projected spend would push us past the
        # available headroom. ``ceiling <= 0`` means there is no
        # headroom at all (reserve >= max, or max itself is zero);
        # we still block on a non-positive ceiling when the call
        # would actually spend anything.
        if would_spend > 0 and projected > ceiling:
            reasons.append("opengod_budget_exceeded")
        return BudgetAssessment(
            allowed=not reasons,
            decision=decision,
            reason_codes=reasons,
            would_spend_usd=would_spend,
            max_usd=self.max_usd,
            projected_used_usd=projected,
        )


__all__ = ["OpenGodBudgetGuard", "BudgetAssessment"]
