"""Repair engine: produces a ``RepairPlan`` from review findings.

A repair plan is created only when at least one finding has a
``recommended_fix`` and a non-empty ``claim``. Otherwise the
engine returns ``None`` so the loop can continue with an
optimization or generic plan.
"""

from __future__ import annotations

from loopos.loop_engine.models import (
    BuildResult,
    RepairPlan,
    ReviewFinding,
    TestResult,
)


class RepairEngine:
    """Emit a ``RepairPlan`` (or ``None``) for an iteration."""

    def repair(
        self,
        findings: list[ReviewFinding],
        tests: TestResult | None,
        build: BuildResult | None = None,
    ) -> RepairPlan | None:
        actionable = [
            f for f in findings
            if f.recommended_fix and f.severity in {"low", "medium", "high", "critical"}
        ]
        if not actionable:
            return None

        # High-severity first.
        actionable.sort(
            key=lambda f: {"critical": 0, "high": 1, "medium": 2, "low": 3}[f.severity]
        )

        priority = _priority_for(actionable[0].severity)
        steps = [f.recommended_fix for f in actionable]
        return RepairPlan(
            source_findings=[f.id for f in actionable],
            steps=steps,
            priority=priority,
            expected_fix=(
                f"Address {len(actionable)} finding(s); first: {actionable[0].claim}"
            ),
            tests_to_run=_tests_to_run(tests, actionable),
        )


def _priority_for(severity: str) -> str:
    return {
        "critical": "critical",
        "high": "high",
        "medium": "medium",
        "low": "low",
    }.get(severity, "medium")


def _tests_to_run(tests: TestResult | None, findings: list[ReviewFinding]) -> list[str]:
    if tests is None:
        return []
    return [f"re-run simulated test: {cmd}" for cmd in tests.commands]


__all__ = ["RepairEngine"]
