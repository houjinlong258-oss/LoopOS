"""Tests for the Ralph-style --completion-promise short-circuit.

The promise is a literal substring: when an iteration's emitted
surface (build summary, test summary, repair-plan steps, optimization
rationale, review-finding claim) contains the promise, the loop
declares early success with status='deliver' and stops. The matched
iteration index is recorded on the state as
``completion_promise_matched_at`` so an audit replay can see exactly
when the loop declared itself done.

The promise is *opt-in* (only active when supplied) and is always
bounded by ``max_iterations`` (the outer budget gate still applies).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loopos.loop_engine.loop import _iteration_emits_promise  # noqa: E402
from loopos.loop_engine.models import (  # noqa: E402
    BuildResult,
    LoopState,
    RepairPlan,
    ReviewFinding,
    TestResult,
    TrainingIteration,
    UserGoal,
)
from loopos.quality.models import QualityScore  # noqa: E402


# ---------------------------------------------------------------------------
# _iteration_emits_promise unit tests
# ---------------------------------------------------------------------------


def _iter_with(summary: str | None = None, test: str | None = None,
               claim: str | None = None, repair_steps: list[str] | None = None
               ) -> TrainingIteration:
    """Build a synthetic iteration with optional surface strings.

    ``test`` populates TestResult.evidence (the closest analogue to a
    human-readable test summary in v0.4.0's TestResult model). The
    promise matcher scans evidence for substring matches.

    Returns a :class:`TrainingIteration` because
    :func:`_iteration_emits_promise` is typed to consume that
    subclass specifically; the extra ``loss`` / ``signals`` fields
    stay at their defaults.
    """
    build = BuildResult(
        iteration_id="it", plan_id="p",
        status="simulated", source="sim",
        summary=summary or "", errors=[], artifacts=[],
    ) if summary is not None else None
    test_res = TestResult(
        iteration_id="it",
        status="simulated", source="sim",
        passed=1, failed=0, skipped=0,
        failures=[], evidence=[test] if test else [],
    ) if test is not None else None
    findings: list[ReviewFinding] = []
    if claim is not None:
        findings.append(ReviewFinding(
            id="f1", category="quality_gap", severity="low",
            claim=claim, evidence=[], blocks_delivery=False,
        ))
    repair: RepairPlan | None = None
    if repair_steps is not None:
        repair = RepairPlan(
            id="r1", source_findings=[], steps=repair_steps,
            priority="low", expected_fix="",
        )
    from loopos.loop_engine.models import PlanCandidate
    plan = PlanCandidate(
        id="p", source="planner", title="t", steps=["s"],
    )
    return TrainingIteration(
        id="it", index=1, goal_id="g",
        plan=plan, build_result=build, test_result=test_res,
        review_findings=findings, repair_plan=repair,
        quality_score=QualityScore(overall=0.5),
    )


class TestPromiseMatching:
    def test_no_promise_no_match(self) -> None:
        assert _iteration_emits_promise(_iter_with(summary="hello"), "") is False
        assert _iteration_emits_promise(_iter_with(summary="hello"), None) is False

    def test_build_summary_match(self) -> None:
        it = _iter_with(summary="Build status: PROJECT_TRAINING_RUNTIME_OK")
        assert _iteration_emits_promise(it, "PROJECT_TRAINING_RUNTIME_OK") is True

    def test_test_summary_match(self) -> None:
        it = _iter_with(test="3 passed, ship_it=true")
        assert _iteration_emits_promise(it, "ship_it=true") is True

    def test_repair_steps_match(self) -> None:
        it = _iter_with(repair_steps=["Patch file", "Update docs: ALL_DONE"])
        assert _iteration_emits_promise(it, "ALL_DONE") is True

    def test_finding_claim_match(self) -> None:
        it = _iter_with(claim="All quality gates passed: GREEN_LIGHT")
        assert _iteration_emits_promise(it, "GREEN_LIGHT") is True

    def test_no_match_returns_false(self) -> None:
        it = _iter_with(summary="still working on it")
        assert _iteration_emits_promise(it, "DONE") is False

    def test_promise_is_substring(self) -> None:
        it = _iter_with(summary="ready to deliver the next iteration")
        assert _iteration_emits_promise(it, "deliver") is True

    def test_promise_with_whitespace_is_stripped(self) -> None:
        it = _iter_with(summary="ready")
        assert _iteration_emits_promise(it, "   ready   ") is True


# ---------------------------------------------------------------------------
# LoopState field tests
# ---------------------------------------------------------------------------


class TestLoopStatePromise:
    def test_default_state_has_no_promise(self) -> None:
        state = LoopState(goal=UserGoal(id="g", raw_goal="x"))
        assert state.completion_promise is None
        assert state.completion_promise_matched_at is None

    def test_state_accepts_promise(self) -> None:
        state = LoopState(
            goal=UserGoal(id="g", raw_goal="x"),
            completion_promise="DONE",
            completion_promise_matched_at=3,
        )
        assert state.completion_promise == "DONE"
        assert state.completion_promise_matched_at == 3

    def test_state_rejects_extra_fields(self) -> None:
        with pytest.raises(Exception):
            LoopState(
                goal=UserGoal(id="g", raw_goal="x"),
                not_a_real_field=True,  # type: ignore[call-arg]
            )


# ---------------------------------------------------------------------------
# End-to-end loop run with promise (uses real engine)
# ---------------------------------------------------------------------------


class TestLoopRunWithPromise:
    """Smoke test: drive the LoopEngine end-to-end with a promise."""

    def test_promise_match_short_circuits(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Use ``monkeypatch.chdir`` rather than ``os.chdir`` so the
        # original working directory is restored at test end. A raw
        # ``os.chdir`` would leak to subsequent tests in the run and
        # break any test that uses relative paths (e.g. the
        # ``Path("loopos/...")`` assertions in
        # ``test_fusion_router_kernel_wiring.py``).
        monkeypatch.chdir(tmp_path)
        from loopos.loop_engine.loop import LoopEngine
        engine = LoopEngine()
        # Inject a custom builder whose summary contains the promise
        # so the loop declares early success on iteration 1.
        from loopos.loop_engine.builder import LoopBuilder
        from loopos.loop_engine.models import PlanCandidate

        promise = "EARLY_BIRD_WINS"

        class _PromisingBuilder(LoopBuilder):
            def build(self, plan: PlanCandidate, iteration_id: str, dry_run: bool = True) -> BuildResult:
                return BuildResult(
                    iteration_id=iteration_id,
                    plan_id=plan.id,
                    status="simulated",
                    source="promising_builder",
                    summary=f"build finished: {promise}",
                    errors=[],
                    artifacts=[],
                )

        engine.builder = _PromisingBuilder()
        state = engine.run(
            goal="drive loop with promise",
            max_iterations=5,
            dry_run=True,
            completion_promise=promise,
        )
        # The loop should have stopped at iteration 1 (not run 5)
        assert state.completion_promise == promise
        assert state.completion_promise_matched_at == 1
        assert len(state.iterations) == 1
        assert state.current_status == "ready_to_deliver"
        last = state.iterations[-1]
        assert last.convergence is not None
        assert last.convergence.status == "deliver"
        assert "completion_promise" in (last.convergence.reason or "")

    def test_no_match_runs_full_budget(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # See test_promise_match_short_circuits for why we use
        # ``monkeypatch.chdir`` rather than ``os.chdir``.
        monkeypatch.chdir(tmp_path)
        from loopos.loop_engine.loop import LoopEngine
        engine = LoopEngine()
        state = engine.run(
            goal="drive loop with promise that never matches",
            max_iterations=3,
            dry_run=True,
            completion_promise="THIS_NEVER_APPEARS_IN_OUTPUT",
        )
        assert state.completion_promise == "THIS_NEVER_APPEARS_IN_OUTPUT"
        assert state.completion_promise_matched_at is None
        # Without a custom convergence decider, the loop ran all 3
        # iterations and left status as "initialized".
        assert len(state.iterations) == 3
        assert state.current_status == "initialized"

    def test_no_promise_means_no_short_circuit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # See test_promise_match_short_circuits for why we use
        # ``monkeypatch.chdir`` rather than ``os.chdir``.
        monkeypatch.chdir(tmp_path)
        from loopos.loop_engine.loop import LoopEngine
        engine = LoopEngine()
        state = engine.run(
            goal="drive loop with no promise",
            max_iterations=3,
            dry_run=True,
        )
        assert state.completion_promise is None
        assert state.completion_promise_matched_at is None
        assert len(state.iterations) == 3


# ---------------------------------------------------------------------------
# CLI surface test
# ---------------------------------------------------------------------------


class TestCompletionPromiseCLI:
    def test_typer_option_appears_in_help(self) -> None:
        from loopos.cli.commands.loop import loop_run_command
        import inspect
        sig = inspect.signature(loop_run_command)
        assert "completion_promise" in sig.parameters
        assert sig.parameters["completion_promise"].default is None