"""v0.3 CLI: ``loopos opengod decide`` command.

OpenGod is a strategic planner; it never executes. The CLI command
emits a JSON document with the decision, verdict, and the evidence
used to make it.
"""

from __future__ import annotations

import json

from loopos.opengod import (
    OpenGodBudgetGuard,
    build_verdict,
    collect_evidence,
    decide,
)


def opengod_command(
    goal_id: str,
    *,
    goal_title: str = "",
    goal_risk: str = "medium",
    fusion_mode: str = "single",
    fusion_score: int = 0,
    hard_fail_count: int = 0,
    readiness_status: str = "unknown",
    adapter_id: str = "",
    live_provider_calls: bool = False,
    budget_used_usd: float = 0.0,
    budget_max_usd: float = 0.0,
    max_budget_usd: float = 1.0,
    reserve_usd: float = 0.10,
    json_output: bool = True,
) -> int:
    context = collect_evidence(
        goal_id=goal_id,
        goal_title=goal_title,
        goal_risk=goal_risk,
        fusion_mode=fusion_mode,
        fusion_score=fusion_score,
        hard_fail_count=hard_fail_count,
        readiness_status=readiness_status,
        adapter_id=adapter_id,
        live_provider_calls=live_provider_calls,
        budget_used_usd=budget_used_usd,
        budget_max_usd=budget_max_usd,
    )
    decision = decide(context)
    verdict = build_verdict(decision)
    guard = OpenGodBudgetGuard(max_usd=max_budget_usd, reserve_usd=reserve_usd)
    assessment = guard.assess(context, decision)
    payload = {
        "schema_version": "0.3",
        "status": "ok",
        "goal_id": goal_id,
        "decision": decision.to_dict(),
        "verdict": verdict.to_dict(),
        "budget_assessment": assessment.model_dump(mode="json"),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


__all__ = ["opengod_command"]
