"""Mad Dog: extreme quality attacker across 10 categories.

Mad Dog in v0.4.0 is **not** a security blocker. It is a quality
attacker that raises findings in 10 categories, and only blocks
delivery when the finding is **evidence-backed**.

The "evidence gate" invariant:

> A ``MadDogFinding`` with ``blocks_delivery=True`` must carry at
> least one entry in ``evidence``. Findings without evidence are
> downgraded to ``blocks_delivery=False``.

Stage classification (v0.4.x):
-----------------------------
Every ``MadDogFinding`` carries a ``stage`` that tells the consumer
how to act on it:

* ``block_now``        — must block delivery right now. Equivalent
  to ``blocks_delivery=True`` (after the evidence gate).
* ``block_next_iter``  — must block the *next* iteration's plan
  selection, but does NOT block current delivery. Surfaced as a
  hard constraint on the Fusion Optimizer.
* ``informational``    — visible to humans, audit-trail only.
  Doesn't block anything.

The stage is **auto-derived** from ``blocks_delivery`` and
``severity`` so legacy callers that only set ``blocks_delivery``
still produce a correct stage. The default stage-resolution rule
(block_now when blocker; block_next_iter when medium-or-higher;
informational otherwise) is exposed as ``resolve_stage`` so the
Fusion Optimizer can re-classify findings without re-instantiating
them.
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
    "visual_verification_gap",
    "security_risk",
]

MadDogSeverity = Literal["info", "low", "medium", "high", "critical"]

# v0.4.x: how the consumer should treat the finding.
MadDogStage = Literal["block_now", "block_next_iter", "informational"]


# Severities that warrant blocking the next iteration's plan
# selection even if the current iteration can still deliver.
_BLOCK_NEXT_SEVERITIES: frozenset[str] = frozenset({"medium", "high", "critical"})


def resolve_stage(blocks_delivery: bool, severity: str) -> MadDogStage:
    """Map the (blocks_delivery, severity) pair to a MadDogStage.

    Rules:

    * ``blocks_delivery=True``   → ``block_now``
    * ``blocks_delivery=False``  → ``block_next_iter`` if severity
      is medium / high / critical, else ``informational``.

    This is the single source of truth for stage resolution; the
    ``MadDogFinding`` validator uses it so legacy and explicit
    stage values stay in sync.
    """
    if blocks_delivery:
        return "block_now"
    if severity in _BLOCK_NEXT_SEVERITIES:
        return "block_next_iter"
    return "informational"


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
    # v0.4.x: the effective stage for this finding. The caller may
    # pass an explicit value; otherwise it is auto-derived from
    # ``(blocks_delivery, severity)`` via :func:`resolve_stage` in
    # the after-validator. Excluded from ``model_dump`` because it
    # is fully derivable from the other fields.
    stage: MadDogStage | None = Field(default=None, exclude=True)
    resolved_stage: MadDogStage | None = None

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

    @model_validator(mode="after")
    def _stage_consistent_with_evidence_gate(self) -> "MadDogFinding":
        """After the evidence-gate pass, populate ``stage``.

        Resolution order:

        1. If the caller passed an explicit ``stage`` value, honour it.
        2. Otherwise derive from ``(blocks_delivery, severity)``
           via :func:`resolve_stage`.

        Both ``stage`` and ``resolved_stage`` are then set to the
        same value so callers reading either field get a consistent
        answer.

        Note: the evidence gate (mode='before') may have downgraded
        ``blocks_delivery`` from True to False when ``evidence`` is
        empty. The after-validator uses the *post-gate*
        ``blocks_delivery`` so the stage is always consistent with
        the public surface.
        """
        if self.stage is None:
            derived = resolve_stage(self.blocks_delivery, self.severity)
            object.__setattr__(self, "stage", derived)
        object.__setattr__(self, "resolved_stage", self.stage)
        return self

    @property
    def blocks_next_iteration(self) -> bool:
        """True when this finding must block the next iteration's plan."""
        return self.stage == "block_next_iter"


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

        # visual_verification_gap
        goal_or_plan = " ".join([state.goal.raw_goal, plan.title, " ".join(plan.steps)]).lower()
        if any(term in goal_or_plan for term in {"ui", "browser", "screen", "visual", "desktop"}):
            has_visual_evidence = bool(tests and any("screenshot" in e or "visual" in e for e in tests.evidence))
            if not has_visual_evidence:
                findings.append(MadDogFinding(
                    category="visual_verification_gap",
                    severity="medium",
                    claim="UI/browser/visual work has no visual verification evidence.",
                    attack="Mad Dog attacks visual completion claims without screen evidence.",
                    evidence=["goal_or_plan references visual surface", "no screenshot/visual evidence"],
                    required_fix="Capture a redacted screenshot or visual verification signal.",
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


__all__ = [
    "MadDogCategory",
    "MadDogFinding",
    "MadDogReviewer",
    "MadDogSeverity",
    "MadDogStage",
    "resolve_stage",
]
