"""Benchmark metrics."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class EvalMetrics(BaseModel):
    success_rate: float
    steps_to_success: float
    command_count: int
    blocked_dangerous_actions: int
    repeated_failure_count: int
    skill_reuse_count: int
    token_estimate: int | None = None


def compute_metrics(results: list[dict[str, Any]]) -> EvalMetrics:
    total = len(results)
    successes = [result for result in results if result.get("success")]
    success_count = len(successes)
    steps = [int(result.get("steps", 0)) for result in successes]
    return EvalMetrics(
        success_rate=(success_count / total) if total else 0.0,
        steps_to_success=(sum(steps) / len(steps)) if steps else 0.0,
        command_count=sum(int(result.get("command_count", 0)) for result in results),
        blocked_dangerous_actions=sum(
            int(result.get("blocked_dangerous_actions", 0)) for result in results
        ),
        repeated_failure_count=sum(int(result.get("repeated_failure_count", 0)) for result in results),
        skill_reuse_count=sum(int(result.get("skill_reuse_count", 0)) for result in results),
        token_estimate=sum(int(result.get("token_estimate", 0)) for result in results)
        if any("token_estimate" in result for result in results)
        else None,
    )
