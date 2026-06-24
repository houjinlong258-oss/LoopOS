"""Tests for v0.4.0 ``loopos.fusion_optimizer``."""

from __future__ import annotations

from loopos.fusion_optimizer import (
    CritiqueEngine,
    EvidenceVerifier,
    FusionOptimizationRequest,
    FusionOptimizer,
    Resolver,
    rank_candidates,
    score_candidate,
)
from loopos.loop_engine import (
    LoopEngine,
    LoopIteration,
    LoopState,
    PlanCandidate,
    SuccessCriteria,
    SuccessCriterion,
)


def _state_with_iteration(goal_text: str = "Build X") -> tuple[LoopState, LoopIteration]:
    eng = LoopEngine()
    state = eng.run(goal_text, max_iterations=1)
    return state, state.iterations[0]


def _basic_request(state: LoopState, prior: LoopIteration) -> FusionOptimizationRequest:
    return FusionOptimizationRequest(
        goal=state.goal,
        success_criteria=state.success_criteria,
        current_state=state,
        previous_iteration=prior,
        mode="consensus",
    )


class TestFusionOptimizer:
    def test_suggests_next_best_iteration(self) -> None:
        state, prior = _state_with_iteration()
        opt = FusionOptimizer()
        result = opt.optimize(_basic_request(state, prior))
        assert result.recommended_next_plan is not None
        assert result.recommended_next_plan.title

    def test_preserves_multiple_plan_candidates(self) -> None:
        state, prior = _state_with_iteration()
        candidates = [
            PlanCandidate(title="A", steps=["a1"], success_criteria_refs=[c.id for c in state.success_criteria.items if c.required]),
            PlanCandidate(title="B", steps=["b1"], rationale="different"),
        ]
        req = FusionOptimizationRequest(
            goal=state.goal,
            success_criteria=state.success_criteria,
            current_state=state,
            previous_iteration=prior,
            candidates=candidates,
            mode="consensus",
        )
        result = FusionOptimizer().optimize(req)
        assert result.recommended_next_plan in candidates
        # The other candidate is in alternatives.
        assert all(a in candidates for a in result.alternatives)

    def test_uses_findings_to_create_repair_plan(self) -> None:
        state, prior = _state_with_iteration()
        # Force a repair plan into the prior iteration.
        from loopos.loop_engine import RepairPlan
        prior.repair_plan = RepairPlan(
            source_findings=["f1"],
            steps=["fix x"],
            priority="high",
            expected_fix="x fixed",
        )
        req = FusionOptimizationRequest(
            goal=state.goal,
            success_criteria=state.success_criteria,
            current_state=state,
            previous_iteration=prior,
            mode="consensus",
        )
        result = FusionOptimizer().optimize(req)
        assert result.repair_plan is not None
        assert result.repair_plan.id == prior.repair_plan.id

    def test_does_not_execute_actions(self) -> None:
        """The optimizer must not have a public execute/dispatch surface."""
        public = {m for m in dir(FusionOptimizer()) if not m.startswith("_")}
        for forbidden in ("dispatch", "execute", "run", "shell", "write_file"):
            assert forbidden not in public, f"Optimizer exposes {forbidden}"

    def test_external_provider_is_optional(self) -> None:
        """Default construction works without any external provider."""
        opt = FusionOptimizer()
        state, prior = _state_with_iteration()
        # No exceptions, no network calls.
        result = opt.optimize(_basic_request(state, prior))
        assert result is not None

    def test_score_candidate_basic(self) -> None:
        sc = SuccessCriteria(items=[
            SuccessCriterion(id="c1", description="a", required=True),
            SuccessCriterion(id="c2", description="b", required=False),
        ])
        c = PlanCandidate(title="x", success_criteria_refs=["c1", "c2"], rationale="r")
        s = score_candidate(c, sc)
        assert s > 0

    def test_critique_engine_finds_empty_steps(self) -> None:
        c = PlanCandidate(title="x", steps=[])
        findings = CritiqueEngine().critique(c, SuccessCriteria(items=[
            SuccessCriterion(id="c1", description="a", required=True),
        ]))
        assert any(f.category == "fake_completion" for f in findings)
        assert any(f.category == "user_goal_mismatch" for f in findings)
        assert any(f.category == "weak_design" for f in findings)

    def test_evidence_verifier_rejects_unknown_refs(self) -> None:
        c = PlanCandidate(title="x", success_criteria_refs=["not_a_real_id"])
        ok, problems = EvidenceVerifier().verify(c, [], SuccessCriteria(items=[
            SuccessCriterion(id="c1", description="a"),
        ]))
        assert ok is False
        assert problems

    def test_resolver_picks_top_candidate(self) -> None:
        c1 = PlanCandidate(title="A", steps=["a"], rationale="r1")
        c2 = PlanCandidate(title="B", steps=["b"], rationale="r2")
        ranked = rank_candidates([c2, c1], SuccessCriteria())
        top, _ = Resolver().resolve(ranked, top_score=0.0)
        assert top.title in {"A", "B"}
