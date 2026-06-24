"""Mad Dog: extreme quality attacker across 10 categories.

Mad Dog in v0.4.0 is **not** a security blocker. It is a quality
attacker that raises findings in 10 categories, and only blocks
delivery when the finding is **evidence-backed**.

The "evidence gate" invariant:

> A ``MadDogFinding`` with ``blocks_delivery=True`` must carry at
> least one entry in ``evidence``. Findings without evidence are
> downgraded to ``blocks_delivery=False``.
"""

from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from loopos.loop_engine.models import (
    BuildResult,
    LoopState,
    PlanCandidate,
    TestResult,
)


MadDogCategory = Literal[
    "fake_completion",
    "fake_convergence",
    "missing_test",
    "weak_design",
    "brittle_flow",
    "implementation_bug",
    "implementation_gap",
    "regression_risk",
    "quality_gap",
    "user_goal_mismatch",
    "documentation_gap",
    "release_gap",
    "token_waste",
    "communication_noise",
    "security_risk",
]

MadDogSeverity = Literal["info", "low", "medium", "high", "critical"]


class MadDogFinding(BaseModel):
    """A single Mad Dog quality attack finding."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"mdf_{uuid4().hex[:8]}")
    category: MadDogCategory
    severity: MadDogSeverity = "medium"
    claim: str
    attack: str = ""
    evidence: list[str] = Field(default_factory=list)
    required_fix: str = ""
    blocks_delivery: bool = False
    affects_convergence: bool = True
    expected_quality_gain_if_fixed: float = 0.0

    @model_validator(mode="before")
    @classmethod
    def _enforce_evidence_gate(cls, data: object) -> object:
        """Drop ``blocks_delivery`` when ``evidence`` is empty.

        The evidence gate: a delivery blocker must be evidence-backed.
        Implemented in ``mode='before'`` so the constructor cannot be
        bypassed.
        """
        if isinstance(data, dict):
            if data.get("blocks_delivery") is True and not data.get("evidence"):
                data = {**data, "blocks_delivery": False}
        return data


class MadDogReviewer:
    """Attack a (plan, build, tests) tuple across 10 quality categories."""

    def review(
        self,
        state: LoopState,
        plan: PlanCandidate,
        build: BuildResult | None,
        tests: TestResult | None,
    ) -> list[MadDogFinding]:
        findings: list[MadDogFinding] = []

        # fake_completion
        if build is not None and build.status == "simulated" and plan.source == "planner":
            findings.append(MadDogFinding(
                category="fake_completion",
                severity="medium",
                claim="Initial plan is a stub; no real work has been done.",
                attack="Mad Dog attacks the claim that 'something was planned' as completion.",
                evidence=["build.status == 'simulated'", "plan.source == 'planner'"],
                required_fix="Plug in a real builder and produce a real build.",
                blocks_delivery=True,
                expected_quality_gain_if_fixed=0.2,
            ))

        # fake_convergence
        if (
            build is not None
            and tests is not None
            and build.status == "simulated"
            and tests.status == "simulated"
            and all(c.satisfied for c in state.success_criteria.items if c.required)
        ):
            findings.append(MadDogFinding(
                category="fake_convergence",
                severity="high",
                claim="The loop looks converged but only simulated evidence exists.",
                attack="Mad Dog attacks clean delivery claims backed only by simulation.",
                evidence=["build.status == 'simulated'", "tests.status == 'simulated'"],
                required_fix="Run a real builder/tester adapter or mark delivery incomplete.",
                blocks_delivery=True,
                expected_quality_gain_if_fixed=0.25,
            ))

        # missing_test
        if tests is not None and tests.passed == 0 and tests.failed == 0:
            findings.append(MadDogFinding(
                category="missing_test",
                severity="medium",
                claim="No tests were executed.",
                attack="Mad Dog attacks the absence of test execution.",
                evidence=["tests.passed == 0 and tests.failed == 0"],
                required_fix="Run the test suite and capture results.",
                blocks_delivery=True,
                expected_quality_gain_if_fixed=0.2,
            ))

        # weak_design
        if not plan.steps:
            findings.append(MadDogFinding(
                category="weak_design",
                severity="high",
                claim="Plan has no steps.",
                attack="Mad Dog attacks the absence of design.",
                evidence=["plan.steps is empty"],
                required_fix="Add concrete steps to the plan.",
                blocks_delivery=True,
                expected_quality_gain_if_fixed=0.15,
            ))

        # brittle_flow
        if len(plan.steps) == 1 and plan.source in {"repair", "optimizer"}:
            findings.append(MadDogFinding(
                category="brittle_flow",
                severity="medium",
                claim="The next-iteration plan has only one step for a repair/optimization path.",
                attack="Mad Dog attacks brittle single-step flows that cannot absorb failures.",
                evidence=[f"plan.source={plan.source}", "len(plan.steps) == 1"],
                required_fix="Break the repair/optimization into verifyable substeps.",
                blocks_delivery=False,
                expected_quality_gain_if_fixed=0.08,
            ))

        # implementation_bug
        if tests is not None and tests.failed > 0:
            findings.append(MadDogFinding(
                category="implementation_bug",
                severity="high",
                claim=f"{tests.failed} test(s) failed.",
                attack="Mad Dog attacks the implementation that broke its own tests.",
                evidence=tests.failures or ["tests.failed > 0"],
                required_fix="Add a failing test, then fix the implementation.",
                blocks_delivery=True,
                expected_quality_gain_if_fixed=0.25,
            ))

        # regression_risk
        if plan.source == "repair" and (tests is None or tests.failed > 0):
            findings.append(MadDogFinding(
                category="regression_risk",
                severity="medium",
                claim="Repair plan did not produce a clean test run.",
                attack="Mad Dog attacks repair plans that introduce new failures.",
                evidence=["plan.source == 'repair'", f"tests.failed == {tests.failed if tests else 0}"],
                required_fix="Verify that the repair does not break the prior test suite.",
                blocks_delivery=False,
                expected_quality_gain_if_fixed=0.1,
            ))

        # quality_gap
        if plan.success_criteria_refs and not plan.rationale:
            findings.append(MadDogFinding(
                category="quality_gap",
                severity="low",
                claim="Plan references criteria but has no rationale.",
                attack="Mad Dog attacks plans that look compliant on the surface.",
                evidence=["plan.success_criteria_refs non-empty", "plan.rationale empty"],
                required_fix="Add a plan rationale.",
                blocks_delivery=False,
                expected_quality_gain_if_fixed=0.05,
            ))

        # user_goal_mismatch
        goal_text = (state.goal.normalized_goal or state.goal.raw_goal).lower()
        for step in plan.steps:
            if step and goal_text and len(goal_text.split()) >= 3:
                # Heuristic: if no step's first word appears in the goal
                # text, flag a possible user_goal_mismatch.
                first_word = step.split()[0].lower()
                if first_word not in goal_text:
                    findings.append(MadDogFinding(
                        category="user_goal_mismatch",
                        severity="low",
                        claim=f"Step '{step[:40]}...' may not align with the goal.",
                        attack="Mad Dog attacks plans whose steps drift from the goal language.",
                        evidence=[f"step: {step[:80]}", f"goal: {goal_text[:80]}"],
                        required_fix="Anchor steps to specific goal words or success criteria.",
                        blocks_delivery=False,
                        expected_quality_gain_if_fixed=0.08,
                    ))
                    break  # one such finding is enough

        # documentation_gap
        for c in state.success_criteria.items:
            if c.type == "doc" and not c.satisfied:
                findings.append(MadDogFinding(
                    category="documentation_gap",
                    severity="low",
                    claim=f"Documentation criterion '{c.description}' is not satisfied.",
                    attack="Mad Dog attacks undocumented work.",
                    evidence=[f"success_criterion.id={c.id}"],
                    required_fix="Add or update the relevant documentation.",
                    blocks_delivery=False,
                    expected_quality_gain_if_fixed=0.05,
                ))

        # release_gap
        if build is not None and build.status == "simulated":
            findings.append(MadDogFinding(
                category="release_gap",
                severity="low",
                claim="Build is simulated; not safe to release.",
                attack="Mad Dog attacks simulated builds as release candidates.",
                evidence=["build.status == 'simulated'"],
                required_fix="Produce a real build artifact before release.",
                blocks_delivery=False,
                expected_quality_gain_if_fixed=0.1,
            ))

        # token_waste
        if len(plan.steps) > 8:
            findings.append(MadDogFinding(
                category="token_waste",
                severity="low",
                claim="Plan carries too many steps for the next iteration.",
                attack="Mad Dog attacks verbose plans that increase token cost without focus.",
                evidence=[f"len(plan.steps) == {len(plan.steps)}"],
                required_fix="Collapse the plan to the smallest verifiable next iteration.",
                blocks_delivery=False,
                expected_quality_gain_if_fixed=0.03,
            ))

        # communication_noise
        normalized_steps = [s.strip().lower() for s in plan.steps if s.strip()]
        if len(normalized_steps) != len(set(normalized_steps)):
            findings.append(MadDogFinding(
                category="communication_noise",
                severity="low",
                claim="Plan repeats the same step more than once.",
                attack="Mad Dog attacks repeated instructions that waste agent context.",
                evidence=["duplicate plan.steps detected"],
                required_fix="Remove duplicated steps before routing the plan.",
                blocks_delivery=False,
                expected_quality_gain_if_fixed=0.03,
            ))

        # security_risk
        # Default: not raised unless an external verifier feeds evidence.
        return findings


__all__ = ["MadDogCategory", "MadDogFinding", "MadDogReviewer", "MadDogSeverity"]
