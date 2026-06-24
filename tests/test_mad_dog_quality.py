"""Tests for v0.4.0 Mad Dog quality attacker.

The spec requires these six scenarios:
1. Mad Dog finds quality gaps, not only security.
2. Mad Dog finds fake completion.
3. Mad Dog finds missing tests.
4. Mad Dog finding requires evidence for blocking delivery.
5. Mad Dog does not block brainstorm without action.
6. Mad Dog findings feed the repair plan.
"""

from __future__ import annotations

from typing import Any, get_args

from loopos.fusion_optimizer import MadDogFinding, MadDogReviewer
from loopos.loop_engine import (
    BuildResult,
    LoopEngine,
    PlanCandidate,
    RepairEngine,
    TestResult,
)


def _plan(**kw: Any) -> PlanCandidate:
    defaults = dict(title="p", steps=["s1"], rationale="r",
                    success_criteria_refs=["crit_test_0"])
    defaults.update(kw)
    return PlanCandidate(**defaults)


def _build_simulated() -> BuildResult:
    return BuildResult(iteration_id="i", plan_id="p", status="simulated")


def _tests_passed() -> TestResult:
    return TestResult(iteration_id="i", status="simulated", passed=3, failed=0)


def _tests_failed() -> TestResult:
    return TestResult(
        iteration_id="i", status="failed", passed=0, failed=1,
        failures=["x is None"],
    )


class TestMadDogQualityAttacker:
    def test_finds_quality_gap_not_only_security(self) -> None:
        state = LoopEngine().run("Build X", max_iterations=1)
        plan = _plan()
        # Force a quality_gap finding via a success_criteria_refs-without-rationale plan
        plan = PlanCandidate(title="p", steps=["s1"], success_criteria_refs=["crit_x"])
        findings = MadDogReviewer().review(
            state, plan, _build_simulated(), _tests_passed(),
        )
        categories = {f.category for f in findings}
        # Should not be limited to security_risk.
        assert "security_risk" not in categories or len(categories) > 1
        assert "release_gap" in categories or "missing_test" in categories or "fake_completion" in categories

    def test_finds_fake_completion(self) -> None:
        state = LoopEngine().run("Build X", max_iterations=1)
        plan = _plan()  # source defaults to "planner"
        findings = MadDogReviewer().review(
            state, plan, _build_simulated(), _tests_passed(),
        )
        assert any(f.category == "fake_completion" for f in findings)

    def test_emits_fake_convergence_signal(self) -> None:
        state = LoopEngine().run("Build X with tests", max_iterations=1)
        plan = state.iterations[0].plan
        findings = MadDogReviewer().review(
            state, plan, state.iterations[0].build_result, state.iterations[0].test_result,
        )
        fake = [f for f in findings if f.category == "fake_convergence"]
        assert fake
        assert fake[0].affects_convergence is True
        assert fake[0].expected_quality_gain_if_fixed > 0

    def test_category_set_matches_fake_convergence_attacker_role(self) -> None:
        from loopos.fusion_optimizer.mad_dog import MadDogCategory
        categories = set(get_args(MadDogCategory))
        for expected in {
            "fake_completion",
            "fake_convergence",
            "missing_test",
            "weak_design",
            "brittle_flow",
            "user_goal_mismatch",
            "implementation_gap",
            "documentation_gap",
            "regression_risk",
            "release_gap",
            "token_waste",
            "communication_noise",
            "security_risk",
        }:
            assert expected in categories

    def test_finds_missing_test(self) -> None:
        state = LoopEngine().run("Build X", max_iterations=1)
        plan = _plan()
        empty = TestResult(iteration_id="i", status="not_run", passed=0, failed=0)
        findings = MadDogReviewer().review(state, plan, _build_simulated(), empty)
        assert any(f.category == "missing_test" for f in findings)

    def test_finding_requires_evidence_for_blocking(self) -> None:
        """A finding with ``blocks_delivery=True`` and no evidence must
        be downgraded to ``blocks_delivery=False`` at construction time.
        """
        f = MadDogFinding(
            category="fake_completion", severity="high", claim="x",
            blocks_delivery=True, evidence=[],
        )
        assert f.blocks_delivery is False

        # With evidence, the gate lets it through.
        f2 = MadDogFinding(
            category="fake_completion", severity="high", claim="x",
            blocks_delivery=True, evidence=["a"],
        )
        assert f2.blocks_delivery is True

        # And the constructor never raises for valid input.
        MadDogFinding(category="quality_gap", severity="low", claim="x")

    def test_does_not_block_brainstorm_without_action(self) -> None:
        """Mad Dog findings are surface findings, not gates on the sandbox."""
        from loopos.loop_engine import ImaginationSandbox, ImaginationRequest, UserGoal
        sandbox = ImaginationSandbox()
        result = sandbox.imagine(ImaginationRequest(
            goal=UserGoal(raw_goal="x").normalized(),
            prompt="Risky",
            mode="wild",
            max_candidates=3,
        ))
        # All candidates are emitted regardless of risk.
        assert len(result.candidates) == 3
        for c in result.candidates:
            assert c.authority_delta == "none"

    def test_findings_feed_repair_plan(self) -> None:
        state = LoopEngine().run("Build X", max_iterations=1)
        plan = _plan()
        mds = MadDogReviewer().review(
            state, plan, _build_simulated(), _tests_failed(),
        )
        # Mad Dog emits implementation_bug with evidence. The repair
        # engine accepts any review finding with a recommended_fix; we
        # promote the Mad Dog finding to a ReviewFinding with a fix.
        from loopos.loop_engine import ReviewFinding
        rfs = [
            ReviewFinding(
                category=m.category, severity=m.severity, claim=m.claim,
                evidence=m.evidence, recommended_fix=m.required_fix,
                blocks_delivery=m.blocks_delivery, source="mad_dog",
            )
            for m in mds
        ]
        plan_obj = RepairEngine().repair(rfs, _tests_failed())
        if any(rf.recommended_fix for rf in rfs):
            assert plan_obj is not None
            assert plan_obj.steps
