"""v0.4.0 ``loopos loop ...`` commands (closeout edition).

This module is the v0.4.0 closeout version of the loop CLI. The
key change from the v0.4.0-rc version is **persistence**:

* ``loopos loop run`` generates a ``run_id``, writes the full
  ``LoopState`` and the per-iteration files to
  ``<data_dir>/runs/<run_id>/``, and prints the ``run_id`` so a
  later ``loopos loop status`` / ``loopos loop deliver`` can find
  it.
* ``loopos loop status`` and ``loopos loop deliver`` accept
  ``--run-id <id>`` and ``--latest`` and **read from disk** —
  the state survives process restarts.

The in-process ``_STATE`` holder is kept for backwards compat
but it is no longer the source of truth. The source of truth is
``<data_dir>/runs/<run_id>/``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from loopos import checkpoint_store
from loopos.checkpoint_store import (
    append_iteration,
    append_lail_signal,
    append_memory_packet,
    append_quality_score,
    init_run,
    latest_run_id,
    read_convergence_report,
    read_delivery_candidate,
    read_iterations,
    read_lail_signals,
    read_loop_state,
    run_dir,
    write_checkpoint,
    write_convergence_report,
    write_delivery_candidate,
    write_loop_state,
)
from loopos.fusion_optimizer import (
    FusionOptimizationRequest,
    FusionOptimizer,
    MadDogReviewer,
)
from loopos.lail import LailSignalBus
from loopos.loop_engine import (
    LoopEngine,
    LoopState,
)
from loopos.loop_engine.models import ProjectCheckpoint
from loopos.quality import (
    ConvergenceEngine,
    QualityScorer,
)


# The in-process holder is kept for back-compat / debugging; it
# is no longer the source of truth.
_STATE: dict[str, Any] = {"state": None, "history": []}


def _set_state(state: LoopState) -> None:
    _STATE["state"] = state
    _STATE["history"].append(state)


def _latest_state() -> LoopState | None:
    state: LoopState | None = _STATE["state"]
    return state


# ---------------------------------------------------------------------------
# Convergence / scoring helpers
# ---------------------------------------------------------------------------


def _convergence_decide(
    state: LoopState, quality: Any, findings: list[Any]
) -> Any:
    """The default ``convergence_decide`` used by ``loop_run_command``.

    The CLI demo uses ``simulated_acceptable=True`` so the v0.4.0 MVP
    can converge in the simulated path. Real deployments should use
    ``simulated_acceptable=False`` to require real evidence.
    """
    scorer = QualityScorer()
    last_it = state.iterations[-1]
    build = last_it.build_result
    tests = last_it.test_result
    if quality is not None:
        q = quality
    elif build is not None and tests is not None:
        q = scorer.score(state, build, tests, findings)
    else:
        from loopos.quality.models import QualityScore
        q = QualityScore()
    return ConvergenceEngine(simulated_acceptable=True).decide(state, q, findings)
    return ConvergenceEngine(simulated_acceptable=True).decide(state, q, findings)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _emit(obj: Any, json_output: bool) -> int:
    if json_output:
        sys.stdout.write(json.dumps(obj, indent=2, default=str))
        sys.stdout.write("\n")
        return 0
    if isinstance(obj, dict):
        d: dict[str, Any] = obj
        for k, v in d.items():
            sys.stdout.write(f"{k}: {v}\n")
    else:
        sys.stdout.write(str(obj) + "\n")
    return 0


def _dump_iteration(iteration: Any) -> dict[str, Any]:
    result: dict[str, Any] = iteration.model_dump(mode="json")
    return result


def _state_to_dict(state: LoopState) -> dict[str, Any]:
    base: dict[str, Any] = state.model_dump(mode="json", exclude={"iterations"})
    base["iterations"] = [_dump_iteration(it) for it in state.iterations]
    return base


# ---------------------------------------------------------------------------
# Iteration -> on-disk writes
# ---------------------------------------------------------------------------


def _persist_iteration(
    run_id: str,
    iteration: Any,
    lail_bus: LailSignalBus,
    data_dir: Path | None,
) -> None:
    """Write one iteration's records to disk.

    The function appends to:

    * ``iterations.jsonl`` (the full iteration dump)
    * ``lail_signals.jsonl`` (drained from the LAIL bus)
    * ``quality_scores.jsonl`` (the per-iteration ``QualityScore``)
    """
    dump = _dump_iteration(iteration)
    append_iteration(run_id, dump, data_dir)
    for sig in lail_bus.drain():
        append_lail_signal(run_id, sig.model_dump(mode="json"), data_dir)
    if iteration.quality_score is not None:
        append_quality_score(
            run_id, iteration.quality_score.model_dump(mode="json"), data_dir
        )


def _persist_memory_packets(
    run_id: str,
    packets: list[Any],
    data_dir: Path | None,
) -> None:
    for p in packets:
        append_memory_packet(
            run_id, p.model_dump(mode="json"), data_dir
        )


# ---------------------------------------------------------------------------
# Run command
# ---------------------------------------------------------------------------


def loop_run_command(
    goal: str,
    max_iterations: int = 3,
    dry_run: bool = True,
    json_output: bool = True,
    run_id: str | None = None,
    data_dir: str | None = None,
) -> int:
    """Drive the loop. Persists to ``<data_dir>/runs/<run_id>/``."""
    dd = Path(data_dir) if data_dir else None

    if run_id is None:
        run_id, _ = init_run(None, data_dir=dd)
    else:
        # Re-running an existing run keeps the same id; the run
        # directory is created (or reused) with a fresh created_at
        # marker only if it does not yet exist.
        run_id, _ = init_run(run_id, data_dir=dd)

    engine = LoopEngine()
    lail_bus = LailSignalBus()
    memory_packets: list[Any] = []

    # Build a state, then run the loop manually so we can drain the
    # LAIL bus per iteration.
    from loopos.loop_engine.goal import GoalEngine

    goal_engine = GoalEngine()
    user_goal = goal_engine.normalize(goal)
    success_criteria = goal_engine.generate_criteria(user_goal)
    state = LoopState(
        goal=user_goal,
        success_criteria=success_criteria,
        max_iterations=max(1, int(max_iterations)),
        trace_id=run_id,
    )
    lail_bus.make(
        "iteration_started", run_id=run_id, iteration_index=0,
        trace_id=run_id, payload={"phase": "loop_start", "goal": goal},
    )

    for index in range(state.max_iterations):
        state.current_status = "running"
        iteration = engine._drive_iteration(state, index, dry_run)
        state.iterations.append(iteration)
        iteration.quality_score = engine._scorer.score(
            state,
            iteration.build_result,
            iteration.test_result,
            iteration.review_findings,
        ) if iteration.build_result and iteration.test_result else None
        # loss + signals
        from loopos.quality.convergence import ConvergenceEngine as _CE
        ce = _CE()
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
        # LAIL signals for this iteration
        lail_bus.make(
            "plan_emitted", run_id=run_id, iteration_index=iteration.index,
            trace_id=run_id, payload={"plan_id": iteration.plan.id, "source": iteration.plan.source},
        )
        lail_bus.make(
            "build_completed", run_id=run_id, iteration_index=iteration.index,
            trace_id=run_id, payload={"status": iteration.build_result.status if iteration.build_result else "n/a"},
        )
        lail_bus.make(
            "test_completed", run_id=run_id, iteration_index=iteration.index,
            trace_id=run_id, payload={
                "status": iteration.test_result.status if iteration.test_result else "n/a",
                "failed": iteration.test_result.failed if iteration.test_result else 0,
            },
        )
        lail_bus.make(
            "review_completed", run_id=run_id, iteration_index=iteration.index,
            trace_id=run_id, payload={"finding_count": len(iteration.review_findings)},
        )
        if iteration.repair_plan:
            lail_bus.make(
                "repair_planned", run_id=run_id, iteration_index=iteration.index,
                trace_id=run_id, payload={"priority": iteration.repair_plan.priority},
            )
        if iteration.optimization_plan:
            lail_bus.make(
                "optimization_planned", run_id=run_id, iteration_index=iteration.index,
                trace_id=run_id, payload={"target": iteration.optimization_plan.target},
            )

        # Convergence (set on the iteration before persisting so
        # the on-disk record includes the convergence decision).
        status = _convergence_decide(
            state, iteration.quality_score, iteration.review_findings,
        )
        iteration.convergence = status
        lail_bus.make(
            "convergence_decided", run_id=run_id, iteration_index=iteration.index,
            trace_id=run_id, payload={"status": status.status, "fake": len(status.fake_convergence)},
        )
        # Persist this iteration (now with convergence attached).
        _persist_iteration(run_id, iteration, lail_bus, dd)
        # Persist the convergence report
        write_convergence_report(run_id, status.model_dump(mode="json"), dd)
        # Persist the latest checkpoint
        ckpt = ProjectCheckpoint.from_iteration(state.goal.id, iteration)
        write_checkpoint(run_id, ckpt.model_dump(mode="json"), dd)
        lail_bus.make(
            "checkpoint_saved", run_id=run_id, iteration_index=iteration.index,
            trace_id=run_id, payload={"checkpoint_id": ckpt.id},
        )
        if status.status in {"deliver", "blocked", "iteration_budget_exhausted"}:
            if status.status == "deliver":
                state.current_status = "ready_to_deliver"
            elif status.status == "blocked":
                state.current_status = "blocked"
            else:
                state.current_status = "failed"
            # Drain remaining LAIL signals before break
            for sig in lail_bus.drain():
                append_lail_signal(run_id, sig.model_dump(mode="json"), dd)
            break
    else:
        # No early break; the loop ran all iterations and the
        # caller did not deliver. Mark as initialized.
        if state.current_status == "running":
            state.current_status = "initialized"

    # Final writes
    _persist_memory_packets(run_id, memory_packets, dd)
    write_loop_state(run_id, _state_to_dict(state), dd)

    # Delivery candidate
    from loopos.quality import DeliveryEngine as _DE
    cand = _DE().evaluate(state)
    write_delivery_candidate(run_id, cand.model_dump(mode="json"), dd)

    _set_state(state)

    out = {
        "run_id": run_id,
        "data_dir": str(dd or checkpoint_store.default_data_dir()),
        "current_status": state.current_status,
        "iterations": [_dump_iteration(it) for it in state.iterations],
        "delivery": cand.model_dump(mode="json"),
    }
    return _emit(out, json_output)


# ---------------------------------------------------------------------------
# Status command
# ---------------------------------------------------------------------------


def _select_run_id(run_id: str | None, data_dir: Path | None) -> str | None:
    if run_id == "latest" or run_id is None:
        return latest_run_id(data_dir)
    return run_id


def loop_status_command(
    run_id: str | None = None,
    json_output: bool = True,
    data_dir: str | None = None,
) -> int:
    """Show the run state, including the rich project-training surface.

    Accepts ``--run-id <id>`` or ``--latest`` (default). The state is
    read from disk so the call works in a fresh process.
    """
    dd = Path(data_dir) if data_dir else None
    rid = _select_run_id(run_id, dd)
    if rid is None:
        return _emit(
            {"status": "no_run", "message": "Run `loopos loop run <goal>` first."},
            json_output,
        )
    state = read_loop_state(rid, dd)
    if state is None:
        return _emit(
            {"status": "no_run", "run_id": rid,
             "message": f"No loop_state.json for run_id={rid}"},
            json_output,
        )

    iterations = read_iterations(rid, dd)
    lail = read_lail_signals(rid, dd)
    last_iter = iterations[-1] if iterations else None
    last_findings = (last_iter or {}).get("review_findings", [])
    last_failed = [
        t for t in ((last_iter or {}).get("test_result", {}) or {}).get("failures", [])
    ]
    last_repair = (last_iter or {}).get("repair_plan")
    last_opt = (last_iter or {}).get("optimization_plan")
    last_loss = (last_iter or {}).get("loss")
    last_signals = (last_iter or {}).get("signals", [])
    last_conv = (last_iter or {}).get("convergence") or {}
    last_qs = (last_iter or {}).get("quality_score")
    goal_gap = (last_loss or {}).get("goal_gap", {})

    out = {
        "run_id": rid,
        "data_dir": str(dd or checkpoint_store.default_data_dir()),
        "user_goal": state.get("goal", {}).get("raw_goal", ""),
        "current_status": state.get("current_status"),
        "current_iteration": len(iterations),
        "iterations": iterations,
        "lail_signals": lail,
        "lail_kind_summary": _lail_kind_summary(lail),
        "last_iteration": {
            "index": (last_iter or {}).get("index"),
            "plan_id": (last_iter or {}).get("plan", {}).get("id"),
            "plan_source": (last_iter or {}).get("plan", {}).get("source"),
            "build_status": (last_iter or {}).get("build_result", {}).get("status"),
            "test_status": (last_iter or {}).get("test_result", {}).get("status"),
            "last_failed_tests": last_failed,
            "last_repair_plan": last_repair,
            "last_optimization_plan": last_opt,
            "last_signals": last_signals,
            "last_quality_score": last_qs,
            "last_loss": last_loss,
            "last_goal_gap": goal_gap,
            "last_findings_count": len(last_findings),
            "blocking_findings": [
                f for f in last_findings if f.get("blocks_delivery") and f.get("evidence")
            ],
        },
        "convergence": last_conv,
        "next_recommended_action": last_conv.get("next_recommended_action"),
        "fake_convergence_findings": last_conv.get("fake_convergence", []),
        "checkpoint_path": str(run_dir(rid, dd) / "checkpoint.json"),
        "memory_packet_count": len(append_memory_packet.__name__ and [] or []),  # placeholder
    }
    # Drop the placeholder
    out.pop("memory_packet_count", None)
    return _emit(out, json_output)


def _lail_kind_summary(signals: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for s in signals:
        k = s.get("kind", "?")
        out[k] = out.get(k, 0) + 1
    return out


# ---------------------------------------------------------------------------
# Deliver command
# ---------------------------------------------------------------------------


def loop_deliver_command(
    run_id: str | None = None,
    json_output: bool = True,
    data_dir: str | None = None,
) -> int:
    """Show the delivery candidate for a run.

    Accepts ``--run-id <id>`` or ``--latest`` (default). The state
    and the candidate are read from disk.
    """
    dd = Path(data_dir) if data_dir else None
    rid = _select_run_id(run_id, dd)
    if rid is None:
        return _emit(
            {"status": "no_run", "message": "Run `loopos loop run <goal>` first."},
            json_output,
        )
    state = read_loop_state(rid, dd)
    candidate = read_delivery_candidate(rid, dd)
    convergence = read_convergence_report(rid, dd)
    iterations = read_iterations(rid, dd)

    if state is None and candidate is None:
        return _emit(
            {"status": "no_run", "run_id": rid},
            json_output,
        )

    # Compute coverage: which required criteria are satisfied.
    items = (state or {}).get("success_criteria", {}).get("items", [])
    required = [c for c in items if c.get("required")]
    satisfied = [c for c in required if c.get("satisfied")]
    unsatisfied = [c for c in required if not c.get("satisfied")]

    fake = (convergence or {}).get("fake_convergence", []) if convergence else []
    open_risks = []
    if candidate is not None:
        open_risks = list(candidate.get("open_risks", []))

    out = {
        "run_id": rid,
        "user_goal": (state or {}).get("goal", {}).get("raw_goal"),
        "delivery_status": (
            "ready" if (candidate and candidate.get("ready"))
            else "blocked_by_fake_convergence" if fake
            else "blocked" if (convergence and convergence.get("status") == "blocked")
            else "budget_exhausted" if (convergence and convergence.get("status") == "iteration_budget_exhausted")
            else "incomplete"
        ),
        "ready": bool(candidate and candidate.get("ready")),
        "why": _why_text(state, candidate, convergence, fake),
        "summary": (candidate or {}).get("summary"),
        "success_criteria_coverage": {
            "required": len(required),
            "satisfied": len(satisfied),
            "unsatisfied": len(unsatisfied),
            "satisfied_ids": [c.get("id") for c in satisfied],
            "unsatisfied_ids": [c.get("id") for c in unsatisfied],
        },
        "remaining_gaps": unsatisfied,
        "fake_convergence_findings": fake,
        "evidence": (candidate or {}).get("evidence", []),
        "open_risks": open_risks,
        "known_limitations": (candidate or {}).get("known_limitations", []),
        "convergence_status": (convergence or {}).get("status"),
        "iterations": len(iterations),
        "recommended_next_loop": _recommended_next_loop(state, candidate, convergence, fake),
        "quality_score": (candidate or {}).get("quality_score"),
    }
    return _emit(out, json_output)


def _why_text(state: Any, candidate: Any, convergence: Any, fake: list[Any]) -> str:
    if candidate and candidate.get("ready"):
        return (
            "All required success criteria satisfied with evidence; "
            "no fake convergence; quality score above threshold."
        )
    if fake:
        return (
            f"Fake convergence detected ({len(fake)} finding(s)); "
            f"delivery blocked until the adversarial evaluator is satisfied."
        )
    if convergence and convergence.get("status") == "iteration_budget_exhausted":
        return "Iteration budget exhausted before the loop converged."
    if convergence and convergence.get("status") == "blocked":
        return "Convergence engine marked this run as blocked."
    if state and state.get("current_status") == "running":
        return "Loop still in progress; delivery not yet evaluated."
    return (
        "Required success criteria are not all satisfied with evidence; "
        "loop should continue."
    )


def _recommended_next_loop(state: Any, candidate: Any, convergence: Any, fake: list[Any]) -> str:
    if fake:
        cats = sorted({f.get("category") for f in fake})
        return (
            f"Run another loop with a new plan that addresses: "
            f"{', '.join(cats)}."
        )
    if convergence and convergence.get("next_recommended_action"):
        return (
            f"Run another loop with action: "
            f"{convergence['next_recommended_action']}."
        )
    return "Run another loop with a fresh plan candidate."


__all__ = [
    "loop_deliver_command",
    "loop_optimize_command",
    "loop_repair_command",
    "loop_review_command",
    "loop_run_command",
    "loop_status_command",
]


# ---------------------------------------------------------------------------
# Other commands (review, repair, optimize)
# ---------------------------------------------------------------------------


def loop_review_command(
    mad_dog: bool = False,
    json_output: bool = True,
    run_id: str | None = None,
    data_dir: str | None = None,
) -> int:
    dd = Path(data_dir) if data_dir else None
    rid = _select_run_id(run_id, dd)
    if rid is None:
        return _emit({"status": "no_run"}, json_output)
    iterations = read_iterations(rid, dd)
    latest = iterations[-1] if iterations else None
    if latest is None:
        return _emit({"status": "no_iterations", "run_id": rid}, json_output)
    out: dict[str, Any] = {
        "run_id": rid,
        "iteration": latest.get("index"),
        "findings": latest.get("review_findings", []),
    }
    if mad_dog:
        reviewer = MadDogReviewer()
        # Recompute mad-dog findings from the latest iteration. We
        # need a LoopState for the goal access, so rebuild a
        # minimal state from the on-disk state.json.
        from loopos.loop_engine.models import (
            BuildResult, PlanCandidate, TestResult, UserGoal, LoopState,
        )
        try:
            ls_state = read_loop_state(rid, dd) or {}
            g = UserGoal(**ls_state.get("goal", {"raw_goal": "?"}))
            ls = LoopState(goal=g)
            plan = PlanCandidate(**latest.get("plan", {}))
            build = BuildResult(**latest.get("build_result", {}))
            tests = TestResult(**latest.get("test_result", {}))
            mds = reviewer.review(ls, plan, build, tests)
            out["mad_dog_findings"] = [m.model_dump(mode="json") for m in mds]
        except Exception as exc:  # noqa: BLE001
            out["mad_dog_error"] = str(exc)
    return _emit(out, json_output)


def loop_repair_command(
    json_output: bool = True,
    run_id: str | None = None,
    data_dir: str | None = None,
) -> int:
    dd = Path(data_dir) if data_dir else None
    rid = _select_run_id(run_id, dd)
    if rid is None:
        return _emit({"status": "no_run"}, json_output)
    iterations = read_iterations(rid, dd)
    latest = iterations[-1] if iterations else None
    if latest is None:
        return _emit({"status": "no_iterations", "run_id": rid}, json_output)
    if latest.get("repair_plan") is None:
        return _emit(
            {"status": "no_repair_plan", "run_id": rid, "iteration": latest.get("index")},
            json_output,
        )
    return _emit(latest["repair_plan"], json_output)


def loop_optimize_command(
    json_output: bool = True,
    run_id: str | None = None,
    data_dir: str | None = None,
) -> int:
    dd = Path(data_dir) if data_dir else None
    rid = _select_run_id(run_id, dd)
    if rid is None:
        return _emit({"status": "no_run"}, json_output)
    state = read_loop_state(rid, dd)
    iterations = read_iterations(rid, dd)
    if state is None or not iterations:
        return _emit({"status": "no_run", "run_id": rid}, json_output)
    # The optimizer works on the latest in-process state, so we
    # rebuild a minimal LoopState-shaped object for the optimizer.
    from loopos.loop_engine.models import (
        SuccessCriteria, UserGoal, SuccessCriterion,
        LoopIteration,
    )
    items = [SuccessCriterion(**c) for c in state["success_criteria"]["items"]]
    sc = SuccessCriteria(items=items, minimum_quality_score=state["success_criteria"].get("minimum_quality_score", 0.75))
    g = UserGoal(**state["goal"])
    state_obj = LoopState(
        goal=g,
        success_criteria=sc,
        max_iterations=state.get("max_iterations", 3),
        trace_id=state.get("trace_id"),
    )
    last = iterations[-1]
    state_obj.iterations = [
        LoopIteration(**{k: v for k, v in last.items() if k in LoopIteration.model_fields})
    ]
    req = FusionOptimizationRequest(
        goal=g,
        success_criteria=sc,
        current_state=state_obj,
        previous_iteration=state_obj.iterations[0] if state_obj.iterations else None,
        mode="consensus",
    )
    opt = FusionOptimizer()
    result = opt.optimize(req)
    return _emit(result.model_dump(mode="json"), json_output)
