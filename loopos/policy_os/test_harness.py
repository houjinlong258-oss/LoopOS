"""Small deterministic Policy OS test harness."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from loopos.policy_os.engine import PolicyEngine


class PolicyTestCase(BaseModel):
    scope: str
    subject: dict[str, Any] = Field(default_factory=dict)
    expected_action: str
    risk_level: str = "low"


def run_policy_cases(engine: PolicyEngine, cases: list[PolicyTestCase]) -> list[str]:
    """Return human-readable failures for policy cases."""

    failures: list[str] = []
    for case in cases:
        decision = engine.evaluate(case.scope, subject=case.subject, risk_level=case.risk_level)
        if decision.action != case.expected_action:
            failures.append(
                f"{case.scope} expected {case.expected_action}, got {decision.action}"
            )
    return failures
