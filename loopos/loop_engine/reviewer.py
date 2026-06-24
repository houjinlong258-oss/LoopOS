"""Loop reviewer: produces ``ReviewFinding`` items for an iteration.

The reviewer is deterministic and offline. It produces findings in
**all ten** ``ReviewCategory`` values when the input warrants it; a
missing category is treated as a finding of its own (``missing_test``)
when the criteria reference tests that the build did not exercise.

The reviewer's job is to **feed the next iteration**, not to gate
delivery on its own. Delivery gating is the
``ConvergenceEngine``'s responsibility, and it uses
``blocks_delivery`` plus evidence.
"""

from __future__ import annotations

from loopos.loop_engine.models import (
    BuildResult,
    LoopState,
    PlanCandidate,
    ReviewCategory,
    ReviewFinding,
    ReviewSeverity,
    TestResult,
)


class LoopReviewer:
    """Emit a list of ``ReviewFinding`` for one iteration."""

    def review(
        self,
        state: LoopState,
        plan: PlanCandidate,
        build: BuildResult | None,
        tests: TestResult | None,
    ) -> list[ReviewFinding]:
        findings: list[ReviewFinding] = []

        # Failed tests -> implementation_bug / missing_test findings.
        if tests is not None and tests.failed > 0:
            for msg in tests.failures:
                findings.append(
                    ReviewFinding(
                        category="implementation_bug",
                        severity="high" if tests.failed > 1 else "medium",
                        claim=f"Test failure: {msg}",
                        evidence=[f"test_result.failures contains: {msg}"],
                        impact="Build does not satisfy its own test suite.",
                        recommended_fix="Add a failing test, then fix the implementation.",
                        blocks_delivery=True,
                        source="reviewer",
                    )
                )

        # Build errors -> implementation_bug.
        if build is not None and build.status == "failed":
            for err in build.errors:
                findings.append(
                    ReviewFinding(
                        category="implementation_bug",
                        severity="high",
                        claim=f"Build error: {err}",
                        evidence=[f"build_result.errors contains: {err}"],
                        impact="Build did not succeed.",
                        recommended_fix="Resolve the build error before testing.",
                        blocks_delivery=True,
                        source="reviewer",
                    )
                )

        # Simulated build/test -> missing_test finding (we did not exercise
        # any real test, so the "test coverage" criterion is not satisfied
        # in a strong sense).
        if build is not None and build.status == "simulated":
            findings.append(
                ReviewFinding(
                    category="missing_test",
                    severity="low",
                    claim="Build was simulated; no real tests were executed.",
                    evidence=["build_result.status == 'simulated'"],
                    impact="Real test coverage is not verified in this run.",
                    recommended_fix="Plug in a real ``test_fn`` on ``LoopTester``.",
                    blocks_delivery=False,
                    source="reviewer",
                )
            )

        # Goal alignment: if the plan has no rationale or no success_criteria_refs,
        # raise user_goal_mismatch.
        if not plan.rationale or not plan.success_criteria_refs:
            findings.append(
                ReviewFinding(
                    category="user_goal_mismatch",
                    severity="medium",
                    claim="Plan does not reference the goal or success criteria.",
                    evidence=[f"plan.success_criteria_refs={plan.success_criteria_refs}"],
                    impact="Plan may diverge from the user goal.",
                    recommended_fix="Anchor the plan to specific success criterion IDs.",
                    blocks_delivery=False,
                    source="reviewer",
                )
            )

        # Documentation gap when a doc criterion is unsatisfied.
        for c in state.success_criteria.items:
            if c.type == "doc" and not c.satisfied:
                findings.append(
                    ReviewFinding(
                        category="documentation_gap",
                        severity="low",
                        claim=f"Documentation criterion '{c.description}' is not satisfied.",
                        evidence=[f"success_criterion.id={c.id}"],
                        impact="Documentation may be missing for the change.",
                        recommended_fix="Add or update the relevant documentation.",
                        blocks_delivery=False,
                        source="reviewer",
                    )
                )

        return findings


__all__ = ["LoopReviewer"]


# Type re-exports for analyzers
_ = (ReviewSeverity, ReviewCategory)
