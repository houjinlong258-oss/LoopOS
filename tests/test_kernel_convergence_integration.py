"""Runtime integration coverage for the kernel convergence handoff."""

from __future__ import annotations

import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

from loopos.ail.models import AILInstruction, AILReason
from loopos.core.isa import InstructionSafety
from loopos.kernel import KernelBoot, KernelConfig, KernelLoopEngine, ReplayEngine, RunSpec
from loopos.kernel.models import RunRecord
from loopos.policy_os.models import PolicyDecision
from loopos.syscalls import SyscallCall, SyscallResult


class StaticIntentCompiler:
    """Compile a fixed instruction sequence against the runtime run id."""

    def __init__(self, specs: Iterable[tuple[str, dict[str, Any]]]) -> None:
        self.specs = list(specs)

    def compile(self, run: RunRecord) -> list[AILInstruction]:
        return [
            AILInstruction(
                run_id=run.run_id,
                step=step,
                op=op,  # type: ignore[arg-type]
                reason=AILReason(code=f"test.{op.lower()}"),
                args={"reason": "test plan complete", **args} if op == "LOOP.HALT" else args,
                safety=InstructionSafety(risk_level="low"),
                metadata={"policy_scope": "instruction.validate"},
            )
            for step, (op, args) in enumerate(self.specs, start=1)
        ]


def _runtime(tmp: str):  # type: ignore[no-untyped-def]
    return KernelBoot().start(
        KernelConfig(workspace=tmp, data_dir=str(Path(tmp) / ".loopos"))
    )


def _result(
    call: SyscallCall,
    *,
    success: bool,
    error: str | None = None,
    output: dict[str, Any] | None = None,
    risk: str = "low",
) -> SyscallResult:
    return SyscallResult(
        syscall_id=call.id,
        run_id=call.run_id,
        instruction_id=call.instruction_id,
        name=call.name,
        success=success,
        output=output or {},
        error=error,
        risk=risk,  # type: ignore[arg-type]
        policy_decision=PolicyDecision(allowed=success, action="allow" if success else "deny"),
    )


def _failed_dispatch(call: SyscallCall, *, step: int = 0) -> SyscallResult:
    del step
    return _result(call, success=False, error="test command failed")


def _handoffs(runtime: Any, run_id: str) -> list[dict[str, Any]]:
    return [
        event.payload
        for event in runtime.trace_store.list(run_id)
        if event.kind == "decision" and event.payload.get("source") == "convergence_to_scheduler"
    ]


def test_kernel_feeds_real_observation_to_convergence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        runtime = _runtime(tmp)
        compiler = StaticIntentCompiler(
            [("TERM.EXEC", {"cmd": "false", "goal_satisfied": True}), ("LOOP.HALT", {})]
        )
        with patch.object(runtime.syscall_router, "dispatch", side_effect=_failed_dispatch):
            run = KernelLoopEngine(runtime, intent_compiler=compiler).run(
                RunSpec(goal="exercise failed observation", workspace=tmp, mode="dry_run")
            )

        handoff = _handoffs(runtime, run.run_id)[0]
        assert handoff["evaluation"]["failed"] is True
        assert handoff["evaluation"]["goal_satisfied"] is False


def test_syscall_failure_flows_through_scheduler_not_direct_halt() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        runtime = _runtime(tmp)
        compiler = StaticIntentCompiler([("TERM.EXEC", {"cmd": "false"}), ("LOOP.HALT", {})])
        with patch.object(runtime.syscall_router, "dispatch", side_effect=_failed_dispatch):
            run = KernelLoopEngine(runtime, intent_compiler=compiler).run(
                RunSpec(goal="exercise scheduler failure", workspace=tmp, mode="dry_run")
            )

        handoffs = _handoffs(runtime, run.run_id)
        assert handoffs
        assert "scheduler_decision" in handoffs[0]
        assert all(event.get("source") != "direct_halt_shortcut" for event in handoffs)
        assert run.status in {"failed", "repairing", "replanning"}


def test_repeated_real_failures_accumulate_in_progress() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        runtime = _runtime(tmp)
        compiler = StaticIntentCompiler(
            [("TERM.EXEC", {"cmd": "false", "attempt": attempt}) for attempt in range(3)]
        )
        with patch.object(runtime.syscall_router, "dispatch", side_effect=_failed_dispatch):
            run = KernelLoopEngine(runtime, intent_compiler=compiler).run(
                RunSpec(goal="exercise repeated failures", workspace=tmp, mode="dry_run")
            )

        snapshot = run.metadata["progress_accumulator"]
        assert snapshot["repeated_failures"] == 3
        handoff = _handoffs(runtime, run.run_id)[-1]
        assert handoff["convergence_action"] == "halt_failure"
        assert handoff["scheduler_decision"]["action"] == "halt_failed"
        assert run.status == "failed"


def test_real_no_progress_triggers_replan() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        runtime = _runtime(tmp)
        compiler = StaticIntentCompiler(
            [("TERM.EXEC", {"cmd": "echo ok", "attempt": attempt}) for attempt in range(3)]
        )

        def dispatch(call: SyscallCall, *, step: int = 0) -> SyscallResult:
            del step
            return _result(call, success=True, output={"progress_score": 0.2})

        with patch.object(runtime.syscall_router, "dispatch", side_effect=dispatch):
            run = KernelLoopEngine(runtime, intent_compiler=compiler).run(
                RunSpec(goal="exercise no progress", workspace=tmp, mode="dry_run")
            )

        assert run.metadata["progress_accumulator"]["no_progress_count"] >= 2
        assert any(
            item["convergence_action"] == "replan"
            or item["scheduler_decision"]["action"] == "replan"
            for item in _handoffs(runtime, run.run_id)
        )


def test_real_repairable_failure_triggers_repair() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        runtime = _runtime(tmp)
        compiler = StaticIntentCompiler([("TERM.EXEC", {"cmd": "false"}), ("LOOP.HALT", {})])
        with patch.object(runtime.syscall_router, "dispatch", side_effect=_failed_dispatch):
            run = KernelLoopEngine(runtime, intent_compiler=compiler).run(
                RunSpec(goal="exercise repair", workspace=tmp, mode="dry_run")
            )

        first = _handoffs(runtime, run.run_id)[0]
        assert first["evaluation"]["repairable"] is True
        assert first["convergence_action"] == "repair"
        assert first["scheduler_decision"]["action"] == "repair"


def test_policy_denied_flows_through_convergence_scheduler_as_blocked() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        runtime = _runtime(tmp)
        compiler = StaticIntentCompiler([("TERM.EXEC", {"cmd": "echo safe"})])
        denied = PolicyDecision(
            allowed=False,
            action="deny",
            risk="blocked",
            safety_level="L5",
            reason_codes=["test.policy_denied"],
        )
        with patch.object(runtime.policy_engine, "evaluate", return_value=denied):
            run = KernelLoopEngine(runtime, intent_compiler=compiler).run(
                RunSpec(goal="exercise policy denial", workspace=tmp, mode="dry_run")
            )

        handoff = _handoffs(runtime, run.run_id)[0]
        assert run.status == "blocked"
        assert handoff["scheduler_decision"]["action"] == "halt_blocked"
        assert handoff["evaluation"]["reason_codes"] == ["policy.blocked"]


def test_hardcoded_goal_satisfied_is_overridden_by_failed_observation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        runtime = _runtime(tmp)
        compiler = StaticIntentCompiler(
            [("TERM.EXEC", {"cmd": "false", "goal_satisfied": True}), ("LOOP.HALT", {})]
        )
        with patch.object(runtime.syscall_router, "dispatch", side_effect=_failed_dispatch):
            run = KernelLoopEngine(runtime, intent_compiler=compiler).run(
                RunSpec(goal="exercise hint override", workspace=tmp, mode="dry_run")
            )

        evaluation = _handoffs(runtime, run.run_id)[0]["evaluation"]
        assert evaluation["goal_satisfied"] is False
        assert evaluation["failed"] is True
        assert run.status != "succeeded"


def test_progress_accumulator_snapshot_round_trips() -> None:
    from loopos.kernel.progress_accumulator import ProgressAccumulatorSnapshot

    snapshot = ProgressAccumulatorSnapshot(
        previous_score=0.2,
        current_score=0.4,
        no_progress_count=2,
        repeated_failures=3,
        repeated_actions=1,
        last_action_fingerprint="action",
        last_failure_fingerprint="failure",
    )
    restored = ProgressAccumulatorSnapshot.model_validate_json(snapshot.model_dump_json())
    assert restored == snapshot


def test_replay_does_not_execute_syscalls_after_accumulator_added() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        runtime = _runtime(tmp)
        compiler = StaticIntentCompiler([("TERM.EXEC", {"cmd": "echo ok"}), ("LOOP.HALT", {})])
        dispatch = Mock(
            side_effect=lambda call, step=0: _result(  # noqa: ARG005
                call, success=True, output={"progress_score": 1.0}
            )
        )
        with patch.object(runtime.syscall_router, "dispatch", dispatch):
            run = KernelLoopEngine(runtime, intent_compiler=compiler).run(
                RunSpec(goal="exercise replay", workspace=tmp, mode="dry_run")
            )
        calls_before = dispatch.call_count

        replay = ReplayEngine(runtime.trace_store).replay(run.run_id, run.step, durable=run)

        assert replay.events
        assert dispatch.call_count == calls_before
