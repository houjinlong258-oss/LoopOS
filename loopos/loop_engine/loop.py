"""LoopEngine: the v0.4.0 product-facing orchestrator.

``LoopEngine.run()`` drives a ``LoopState`` through the
Goal -> Plan -> Build -> Test -> Review -> Repair -> Optimize ->
Deliver cycle. Each phase produces typed data that the next phase
consumes. The data flow is real in v0.4.0:

* Failed tests raise ``implementation_bug`` findings.
* Findings raise a ``RepairPlan`` whose ``source_findings`` are
  the finding IDs.
* A repair plan drives the next ``PlanCandidate.source="repair"``.
* ``user_goal_mismatch`` and ``quality_gap`` findings drive
  ``OptimizationPlan`` and ``source="optimizer"``.
* The convergence / delivery layers in ``loopos.quality`` decide
  when the loop halts and emit a ``DeliveryCandidate``.

The executors (planner, builder, tester, reviewer, optimizer, repair)
are pluggable. The defaults are deterministic, offline, and
simulated. They can be swapped out without changing the engine.
"""

from __future__ import annotations

from typing import Any, Callable
from uuid import uuid4

from loopos.loop_engine.builder import LoopBuilder
from loopos.loop_engine.checkpoint import InMemoryCheckpointStore
from loopos.loop_engine.commitment import (
    CommitmentBoundary,
    CommitmentDecision,
    CommitmentProposal,
)
from loopos.loop_engine.events import LoopEvent, LoopEventKind
from loopos.loop_engine.goal import GoalEngine
from loopos.loop_engine.interfaces import (
    Builder,
    Optimizer,
    Planner,
    RepairPlanner,
    Reviewer,
    Tester,
)
from loopos.loop_engine.models import (
    LoopIteration,
    LoopState,
    LoopStatus,
    ProjectCheckpoint,
    ReviewFinding,
    SuccessCriteria,
    TrainingIteration,
    UserGoal,
)
from loopos.loop_engine.optimizer import LoopOptimizer
from loopos.loop_engine.planner import LoopPlanner
from loopos.loop_engine.repair import RepairEngine
from loopos.loop_engine.reviewer import LoopReviewer
from loopos.loop_engine.tester import LoopTester
from loopos.loop_engine.trace import LoopTraceRecorder
from loopos.quality.models import QualityScore
from loopos.quality.scorer import QualityScorer


ConvergenceDecider = Callable[[LoopState, QualityScore | None, list[ReviewFinding]], Any]


def _iteration_emits_promise(iteration: TrainingIteration, promise: str | None) -> bool:
    """Return True if the iteration's emitted surface contains ``promise``.

    The match is a literal substring check across the iteration's
    user-visible surface: build summary, test summary, repair plan
    summary, optimization plan summary, and review-finding claims.
    We deliberately do NOT match against internal ids / trace IDs —
    those are not user-visible.

    ``promise`` is typed ``str | None`` because the loop engine
    passes ``state.completion_promise`` directly, which is optional;
    a falsy ``promise`` (``""``, ``None``, whitespace-only) always
    returns ``False`` so the loop does not short-circuit on a
    misconfigured CLI.
    """
    if not promise:
        return False
    needle = promise.strip()
    if not needle:
        return False
    candidates: list[str] = []
    if iteration.build_result is not None:
        candidates.append(iteration.build_result.summary or "")
        for art in iteration.build_result.artifacts or []:
            candidates.append(str(art))
    if iteration.test_result is not None:
        # TestResult has no `summary` field; surface the structured
        # fields the user typically reads: failures, commands, evidence.
        for s in (iteration.test_result.failures or []):
            candidates.append(str(s))
        for s in (iteration.test_result.commands or []):
            candidates.append(str(s))
        for s in (iteration.test_result.evidence or []):
            candidates.append(str(s))
    if iteration.repair_plan is not None:
        candidates.append(" ".join(iteration.repair_plan.steps or []))
    if iteration.optimization_plan is not None:
        candidates.append(getattr(iteration.optimization_plan, "rationale", "") or "")
        candidates.append(getattr(iteration.optimization_plan, "summary", "") or "")
    for f in iteration.review_findings or []:
        candidates.append(f.claim or "")
    return any(needle in c for c in candidates)


class LoopEngine:
    """The v0.4.0 loop engine."""

    def __init__(
        self,
        goal_engine: GoalEngine | None = None,
        planner: Planner | None = None,
        builder: Builder | None = None,
        tester: Tester | None = None,
        reviewer: Reviewer | None = None,
        repair_engine: RepairPlanner | None = None,
        optimizer: Optimizer | None = None,
        commitment_boundary: CommitmentBoundary | None = None,
        trace_recorder: LoopTraceRecorder | None = None,
        checkpoint_store: InMemoryCheckpointStore | None = None,
        scorer: QualityScorer | None = None,
        on_iteration: Callable[[LoopIteration], None] | None = None,
    ) -> None:
        self.goal_engine = goal_engine or GoalEngine()
        self.planner = planner or LoopPlanner()
        self.builder = builder or LoopBuilder()
        self.tester = tester or LoopTester()
        self.reviewer = reviewer or LoopReviewer()
        self.repair_engine = repair_engine or RepairEngine()
        self.optimizer = optimizer or LoopOptimizer()
        self.commitment_boundary = commitment_boundary or CommitmentBoundary()
        self.trace_recorder = trace_recorder or LoopTraceRecorder()
        self.checkpoint_store = checkpoint_store or InMemoryCheckpointStore()
        self._scorer = scorer or QualityScorer()
        self.on_iteration = on_iteration

    def run(
        self,
        goal: UserGoal | str,
        success_criteria: SuccessCriteria | None = None,
        max_iterations: int = 3,
        dry_run: bool = True,
        real_executor: bool = False,
        sandbox: bool = True,
        repo_path: str | None = None,
        test_command: list[str] | None = None,
        convergence_decide: ConvergenceDecider | None = None,
        completion_promise: str | None = None,
    ) -> LoopState:
        """Drive the loop to convergence (or budget exhaustion).

        ``convergence_decide`` is an optional callable with signature
        ``(state, quality, findings) -> ConvergenceStatus``. When not
        provided, the loop runs the configured ``max_iterations`` and
        leaves ``state.current_status`` to the caller (or to the
        ``loopos.quality`` layer when used together).

        ``completion_promise`` is an opt-in Ralph-style short-circuit: when
        any iteration's emitted surface (build summary, test summary,
        review findings) contains the promise string, the loop records a
        successful early completion and stops. The matched iteration index
        is recorded on the state as ``completion_promise_matched_at`` so
        the audit trail can replay when the loop declared itself done.
        """
        # 1. Understand the goal.
        original_adapters: tuple[Builder, Tester, Reviewer] | None = None
        if real_executor:
            if repo_path is None:
                raise ValueError("repo_path is required when real_executor=True")
            from loopos.executors import (
                ExecutionMode,
                RealProjectBuilder,
                RealProjectReviewer,
                RealProjectTester,
            )

            mode = ExecutionMode(
                dry_run=dry_run,
                sandbox=sandbox,
                real_executor=True,
                allow_shell=not dry_run,
                allow_file_write=not dry_run,
                allow_network=False,
                sandbox_root=repo_path if sandbox else None,
            )
            original_adapters = (self.builder, self.tester, self.reviewer)
            self.builder = RealProjectBuilder(repo_path, mode=mode)
            self.tester = RealProjectTester(repo_path, mode=mode, command=test_command)
            self.reviewer = RealProjectReviewer()
        normalized = self.goal_engine.normalize(goal)
        if isinstance(normalized, str):  # pragma: no cover - defensive
            raise TypeError("GoalEngine.normalize must return a UserGoal")
        if success_criteria is None:
            success_criteria = self.goal_engine.generate_criteria(normalized)

        state = LoopState(
            goal=normalized,
            success_criteria=success_criteria,
            max_iterations=max(1, int(max_iterations)),
            trace_id=f"loop_{uuid4().hex[:8]}",
            completion_promise=(completion_promise or None) or None,
        )
        self._record(LoopEvent(kind=LoopEventKind.LOOP_STARTED, trace_id=state.trace_id))

        try:
            for index in range(state.max_iterations):
                state.current_status = "running"
                iteration = self._drive_iteration(state, index, dry_run)
                # Append FIRST so the scorer can see this iteration via
                # state.latest_iteration() (the scorer inspects the plan
                # to compute goal_alignment).
                state.iterations.append(iteration)
                iteration.quality_score = self._scorer.score(
                    state,
                    iteration.build_result,
                    iteration.test_result,
                    iteration.review_findings,
                ) if iteration.build_result and iteration.test_result else None
                # Populate the project-training-loop surface: loss +
                # evaluation signals. These are the gradient that the
                # optimizer consumes on the next iteration.
                from loopos.quality.convergence import ConvergenceEngine
                ce = ConvergenceEngine()
                iteration.loss = ce.compute_loss(
                    state, iteration.quality_score, iteration.review_findings,
                )
                from loopos.loop_engine.models import EvaluationSignal
                iteration.signals = [
                    EvaluationSignal(
                        id=f"sig_{f.id}",
                        source="mad_dog" if f.source == "mad_dog" else "reviewer",
                        category=f.category,
                        severity=f.severity,
                        claim=f.claim,
                        evidence=list(f.evidence),
                        proposed_step=f.recommended_fix,
                        targets_loss_dim=(
                            "blocking_findings" if f.blocks_delivery else "unsat_required"
                        ),
                    )
                    for f in iteration.review_findings
                ]
                self.checkpoint_store.save(
                    ProjectCheckpoint.from_iteration(
                        state.goal.id,
                        iteration,
                        state.success_criteria,
                    )
                )
                self._record(
                    LoopEvent(
                        kind=LoopEventKind.ITERATION_COMPLETED,
                        iteration_index=iteration.index,
                        trace_id=state.trace_id,
                    )
                )
                if self.on_iteration is not None:
                    self.on_iteration(iteration)
                # Ralph-style completion promise: if the user asked us to
                # stop on a literal string match and the iteration's
                # emitted surface contains it, declare early success and
                # break out of the iteration loop. This is opt-in (only
                # active when ``completion_promise`` was passed) and
                # always bounded by ``max_iterations`` (the outer loop's
                # budget gate still applies).
                if state.completion_promise and _iteration_emits_promise(
                    iteration, state.completion_promise
                ):
                    state.completion_promise_matched_at = iteration.index
                    from loopos.loop_engine.models import ConvergenceReport as _CR
                    iteration.convergence = _CR(
                        status="deliver",
                        reason=(
                            f"completion_promise {state.completion_promise!r} "
                            f"matched at iteration {iteration.index}"
                        ),
                        satisfied_criteria=list(state.success_criteria.required_tests or []),
                        unsatisfied_criteria=[],
                        next_recommended_action=None,
                        fake_convergence=[],
                    )
                    state.current_status = "ready_to_deliver"
                    self._record(
                        LoopEvent(
                            kind=LoopEventKind.CONVERGENCE_DECIDED,
                            iteration_index=iteration.index,
                            trace_id=state.trace_id,
                            payload={
                                "status": "deliver",
                                "reason": "completion_promise",
                            },
                        )
                    )
                    self._record(LoopEvent(kind=LoopEventKind.LOOP_DELIVERED, trace_id=state.trace_id))
                    break
                if convergence_decide is not None:
                    status = convergence_decide(
                        state,
                        iteration.quality_score,
                        iteration.review_findings,
                    )
                    iteration.convergence = status
                    self._record(
                        LoopEvent(
                            kind=LoopEventKind.CONVERGENCE_DECIDED,
                            iteration_index=iteration.index,
                            trace_id=state.trace_id,
                            payload={"status": status.status if status else "n/a"},
                        )
                    )
                    if status is not None and status.status in {"deliver", "blocked", "iteration_budget_exhausted"}:
                        state.current_status = _map_status(status.status)
                        if status.status == "deliver":
                            self._record(LoopEvent(kind=LoopEventKind.LOOP_DELIVERED, trace_id=state.trace_id))
                        else:
                            self._record(LoopEvent(kind=LoopEventKind.LOOP_HALTED, trace_id=state.trace_id))
                        break
        finally:
            if original_adapters is not None:
                self.builder, self.tester, self.reviewer = original_adapters

        if state.current_status == "running":
            # Caller did not provide a convergence decider, or no
            # decision was reached: leave the state in a known shape.
            state.current_status = "initialized"
        return state

    def commit(
        self,
        proposal: CommitmentProposal,
    ) -> CommitmentDecision:
        """Bridge an idea to an action via the commitment boundary."""
        return self.commitment_boundary.commit(proposal)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _drive_iteration(
        self,
        state: LoopState,
        index: int,
        dry_run: bool,
    ) -> TrainingIteration:
        iteration_id = f"iter_{index + 1}_{uuid4().hex[:6]}"
        self._record(
            LoopEvent(
                kind=LoopEventKind.ITERATION_STARTED,
                iteration_index=index + 1,
                trace_id=state.trace_id,
            )
        )

        # Plan
        plan = self.planner.plan(state)
        self._record(
            LoopEvent(
                kind=LoopEventKind.PLAN_EMITTED,
                iteration_index=index + 1,
                trace_id=state.trace_id,
                payload={"plan_id": plan.id, "source": plan.source},
            )
        )

        # Build
        build = self.builder.build(plan, iteration_id, dry_run=dry_run)
        self._record(
            LoopEvent(
                kind=LoopEventKind.BUILD_COMPLETED,
                iteration_index=index + 1,
                trace_id=state.trace_id,
                payload={"build_status": build.status},
            )
        )

        # Test
        tests = self.tester.test(build, state.success_criteria, iteration_id, dry_run=dry_run)
        # Real data flow: failed tests must mark test criteria unsatisfied;
        # passing tests mark them satisfied. Other criteria (functional,
        # user_alignment, doc, delivery, quality) are marked satisfied
        # when the simulated test passes — this is the v0.4.0 default
        # for the simulated executor. Real executors are expected to set
        # these explicitly via ``SuccessCriteria.mark_satisfied``.
        if tests.failed > 0:
            for c in state.success_criteria.items:
                if c.type == "test":
                    c.satisfied = False
        elif tests.passed > 0:
            for c in state.success_criteria.items:
                if c.required:
                    c.satisfied = True
                    if not c.evidence:
                        c.evidence.append(f"tests.passed={tests.passed}")
        self._record(
            LoopEvent(
                kind=LoopEventKind.TEST_COMPLETED,
                iteration_index=index + 1,
                trace_id=state.trace_id,
                payload={"test_status": tests.status, "failed": tests.failed},
            )
        )

        # Review
        findings = self.reviewer.review(state, plan, build, tests)
        self._record(
            LoopEvent(
                kind=LoopEventKind.REVIEW_COMPLETED,
                iteration_index=index + 1,
                trace_id=state.trace_id,
                payload={"finding_count": len(findings)},
            )
        )

        # Repair
        repair = self.repair_engine.repair(findings, tests, build)
        if repair is not None:
            self._record(
                LoopEvent(
                    kind=LoopEventKind.REPAIR_PLANNED,
                    iteration_index=index + 1,
                    trace_id=state.trace_id,
                    payload={"repair_id": repair.id, "priority": repair.priority},
                )
            )

        # Optimize
        opt = self.optimizer.optimize(state, findings)
        if opt is not None:
            self._record(
                LoopEvent(
                    kind=LoopEventKind.OPTIMIZATION_PLANNED,
                    iteration_index=index + 1,
                    trace_id=state.trace_id,
                    payload={"optimization_id": opt.id, "target": opt.target},
                )
            )

        return TrainingIteration(
            id=iteration_id,
            index=index + 1,
            goal_id=state.goal.id,
            plan=plan,
            build_result=build,
            test_result=tests,
            review_findings=findings,
            repair_plan=repair,
            optimization_plan=opt,
        )

    def _record(self, event: LoopEvent) -> None:
        self.trace_recorder.record(event)


def _map_status(convergence_status: str) -> LoopStatus:
    if convergence_status == "deliver":
        return "ready_to_deliver"
    if convergence_status == "blocked":
        return "blocked"
    if convergence_status == "iteration_budget_exhausted":
        return "failed"
    return "running"


__all__ = ["LoopEngine"]
