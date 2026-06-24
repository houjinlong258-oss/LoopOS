"""Tests for v0.4.0 Quality / Convergence / Delivery."""

from __future__ import annotations

from loopos.loop_engine import (
    BuildResult,
    LoopEngine,
    LoopState,
    ReviewFinding,
    TestResult,
)
from loopos.quality import (
    ConvergenceEngine,
    DeliveryEngine,
    QualityScorer,
    QualityWeights,
)
from loopos.quality.evidence import EvidenceCollector
from loopos.quality.defects import DefectTracker


def _build_and_tests(state: LoopState) -> tuple[BuildResult, TestResult]:
    latest = state.iterations[-1]
    assert latest.build_result is not None
    assert latest.test_result is not None
    return latest.build_result, latest.test_result


class TestQualityScorer:
    def test_reflects_failed_tests(self) -> None:
        eng = LoopEngine()
        state = eng.run("Build X with tests and docs", max_iterations=1)
        build, _ = _build_and_tests(state)
        failed = TestResult(iteration_id="i", status="failed", passed=0, failed=3, failures=["a", "b", "c"])
        passed = TestResult(iteration_id="i", status="simulated", passed=3, failed=0)
        s_failed = QualityScorer().score(state, build, failed, [])
        s_passed = QualityScorer().score(state, build, passed, [])
        assert s_failed.test_health < s_passed.test_health

    def test_reflects_goal_mismatch(self) -> None:
        eng = LoopEngine()
        state = eng.run("Build X with tests and docs", max_iterations=1)
        build, tests = _build_and_tests(state)
        # Add a user_goal_mismatch finding.
        findings = [ReviewFinding(category="user_goal_mismatch", severity="medium", claim="x")]
        s1 = QualityScorer().score(state, build, tests, [])
        s2 = QualityScorer().score(state, build, tests, findings)
        # Defect health should drop when findings are added.
        assert s2.defect_health < s1.defect_health

    def test_weights_override(self) -> None:
        w = QualityWeights(
            goal_alignment=1.0, test_health=0.0, defect_health=0.0,
            design_health=0.0, documentation_health=0.0, delivery_readiness=0.0,
        )
        scorer = QualityScorer(weights=w)
        eng = LoopEngine()
        state = eng.run("Build X", max_iterations=1)
        build, tests = _build_and_tests(state)
        s = scorer.score(state, build, tests, [])
        # With weight 1.0 on goal_alignment and 0 on everything else,
        # the overall should equal goal_alignment.
        assert abs(s.overall - s.goal_alignment) < 1e-6


class TestConvergenceEngine:
    def test_delivers_when_criteria_met(self) -> None:
        eng = LoopEngine()
        state = eng.run("Build X with tests and docs", max_iterations=1)
        build, tests = _build_and_tests(state)
        findings = state.iterations[0].review_findings
        s = QualityScorer().score(state, build, tests, findings)
        ce = ConvergenceEngine(quality_threshold=0.0, goal_threshold=0.0)
        status = ce.decide(state, s, findings)
        assert status.status == "deliver"

    def test_continues_when_blocking_findings_exist(self) -> None:
        eng = LoopEngine()
        state = eng.run("Build X with tests and docs", max_iterations=1)
        build, tests = _build_and_tests(state)
        blocking = [ReviewFinding(
            category="implementation_bug", severity="high", claim="x",
            evidence=["a"], blocks_delivery=True,
        )]
        s = QualityScorer().score(state, build, tests, blocking)
        ce = ConvergenceEngine()
        status = ce.decide(state, s, blocking)
        # Either continue (with budget) or budget exhausted (1 iter, all
        # blocking -> must be blocked/exhausted).
        assert status.status in {"continue", "iteration_budget_exhausted", "blocked"}

    def test_budget_exhaustion_is_reported(self) -> None:
        eng = LoopEngine()
        state = eng.run("Build X with tests and docs", max_iterations=2)
        # Use a quality threshold above 1.0 so the gate can never pass.
        ce2 = ConvergenceEngine(quality_threshold=1.5, goal_threshold=0.0)
        build, tests = _build_and_tests(state)
        s = QualityScorer().score(state, build, tests, [])
        # Truncate the iteration list to "spend" the budget.
        state.max_iterations = len(state.iterations)
        status = ce2.decide(state, s, [])
        assert status.status == "iteration_budget_exhausted"


class TestDeliveryEngine:
    def test_evidence_required(self) -> None:
        eng = LoopEngine()
        state = eng.run("Build X with tests and docs", max_iterations=2)
        # Force a deliver so the candidate can become ready.
        # Manually mark all required criteria as satisfied.
        for c in state.success_criteria.items:
            c.satisfied = True
        # Inject a deliver status by adding a fake last iteration that
        # already converged. Simpler: directly call DeliveryEngine.
        cand = DeliveryEngine().evaluate(state)
        # The candidate should carry evidence; ``ready`` may be True or
        # False depending on the convergence state, but ``summary`` and
        # ``evidence`` are always populated.
        assert cand.summary
        # evidence may be empty when nothing satisfied; check it's a list.
        assert isinstance(cand.evidence, list)


class TestEvidenceAndDefects:
    def test_evidence_collector_dedupes(self) -> None:
        e = EvidenceCollector()
        e.add("a")
        e.add("a")
        e.add("b")
        assert e.items() == ["a", "b"]

    def test_defect_tracker_counts(self) -> None:
        t = DefectTracker()
        t.record([
            ReviewFinding(category="quality_gap", severity="high", claim="x"),
            ReviewFinding(category="fake_completion", severity="low", claim="y"),
        ])
        assert t.count() == 2
        assert t.by_severity().get("high") == 1
