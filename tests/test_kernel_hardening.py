"""Tests for System Kernel Hardening — invariants, checkpoint, supervisor, lifecycle."""

import tempfile

from loopos.kernel.checkpoint import CheckpointStore, KernelCheckpoint
from loopos.kernel.invariants import KernelInvariantChecker
from loopos.kernel.lifecycle import KernelLifecycle
from loopos.kernel.models import RunRecord, RunSpec
from loopos.kernel.signals import KernelSignalEvent
from loopos.kernel.supervisor import Supervisor, SupervisorConfig
from loopos.kernel.transition import TransitionEngine


# ── Transition Tests ──────────────────────────────────────────


def test_legal_transition_pending_to_running() -> None:
    run = RunRecord.from_spec(RunSpec(goal="test"))
    engine = TransitionEngine()
    engine.apply(run, "running", "EXECUTING")
    assert run.status == "running"


def test_illegal_transition_succeeded_to_running() -> None:
    run = RunRecord.from_spec(RunSpec(goal="test"))
    run.status = "succeeded"
    run.phase = "HALTED"
    engine = TransitionEngine()
    try:
        engine.apply(run, "running", "EXECUTING")
        assert False, "should have raised"
    except ValueError as e:
        assert "invalid" in str(e).lower()


def test_transition_cancelled_to_running_rejected() -> None:
    run = RunRecord.from_spec(RunSpec(goal="test"))
    run.status = "cancelled"
    run.phase = "HALTED"
    engine = TransitionEngine()
    try:
        engine.apply(run, "running", "EXECUTING")
        assert False, "should have raised"
    except ValueError:
        pass


# ── Lifecycle Tests ───────────────────────────────────────────


def test_lifecycle_boot_to_ready() -> None:
    lc = KernelLifecycle()
    lc.transition("booting", reason="init")
    lc.transition("ready", reason="loaded")
    assert lc.phase == "ready"
    assert lc.is_active


def test_lifecycle_invalid_jump() -> None:
    lc = KernelLifecycle()
    try:
        lc.transition("running")
        assert False, "should have raised"
    except ValueError:
        pass


def test_lifecycle_terminated_is_final() -> None:
    lc = KernelLifecycle()
    lc.transition("booting")
    lc.transition("ready")
    lc.transition("shutting_down")
    lc.transition("terminated")
    assert not lc.is_active
    try:
        lc.transition("ready")
        assert False, "should have raised"
    except ValueError:
        pass


# ── Invariant Tests ───────────────────────────────────────────


def test_invariant_syscall_without_policy() -> None:
    checker = KernelInvariantChecker()
    events = [
        {"kind": "instruction", "payload": {"op": "FILE.WRITE"}},
        {"kind": "observation", "payload": {"success": True}},
    ]
    violations = checker.check_all("run-1", 1, events)
    assert any(v.invariant_id == "I1_POLICY_BEFORE_SYSCALL" for v in violations)


def test_invariant_no_violation_when_policy_present() -> None:
    checker = KernelInvariantChecker()
    events = [
        {"kind": "instruction", "payload": {"op": "FILE.WRITE"}},
        {"kind": "policy", "payload": {"allowed": True}},
        {"kind": "observation", "payload": {"success": True}},
    ]
    violations = checker.check_all("run-1", 1, events)
    # Should have no blocker violations
    blockers = [v for v in violations if v.severity == "blocker"]
    assert len(blockers) == 0


def test_invariant_instruction_observation_gap() -> None:
    checker = KernelInvariantChecker()
    events = [
        {"kind": "instruction", "payload": {"op": "PLAN"}},
    ]
    violations = checker.check_all("run-1", 1, events)
    assert any(v.invariant_id == "I2_INSTRUCTION_OBSERVATION_GAP" for v in violations)


def test_invariant_resume_without_approval() -> None:
    checker = KernelInvariantChecker()
    events = [
        {
            "kind": "transition",
            "payload": {
                "before": {"status": "waiting_approval"},
                "after": {"status": "running"},
            },
        },
    ]
    violations = checker.check_approval_resume("run-1", 5, events)
    assert any(v.invariant_id == "I6_RESUME_WITHOUT_APPROVAL" for v in violations)


def test_invariant_resume_with_approval() -> None:
    checker = KernelInvariantChecker()
    events = [
        {"kind": "signal", "payload": {"signal": "approve"}},
        {
            "kind": "transition",
            "payload": {
                "before": {"status": "waiting_approval"},
                "after": {"status": "running"},
            },
        },
    ]
    violations = checker.check_approval_resume("run-1", 5, events)
    assert len(violations) == 0


# ── Checkpoint Tests ──────────────────────────────────────────


def test_checkpoint_from_run() -> None:
    run = RunRecord.from_spec(RunSpec(goal="test checkpoint"))
    cp = KernelCheckpoint.from_run(run)
    assert cp.run_id == run.run_id
    assert cp.checksum
    assert cp.verify()


def test_checkpoint_checksum_stable() -> None:
    run = RunRecord.from_spec(RunSpec(goal="stable test"))
    cp1 = KernelCheckpoint.from_run(run)
    cp2 = KernelCheckpoint.from_run(run)
    assert cp1.checksum == cp2.checksum


def test_checkpoint_store_save_load() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        store = CheckpointStore(tmpdir)
        run = RunRecord.from_spec(RunSpec(goal="store test"))
        cp = KernelCheckpoint.from_run(run)
        store.save(cp)
        loaded = store.load(run.run_id, cp.step)
        assert loaded.checksum == cp.checksum
        assert loaded.verify()


def test_checkpoint_store_list() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        store = CheckpointStore(tmpdir)
        run = RunRecord.from_spec(RunSpec(goal="list test"))
        for step in range(3):
            run.step = step
            cp = KernelCheckpoint.from_run(run)
            store.save(cp)
        items = store.list(run.run_id)
        assert len(items) == 3


# ── Supervisor Tests ──────────────────────────────────────────


def test_supervisor_continue() -> None:
    run = RunRecord.from_spec(RunSpec(goal="normal"))
    sv = Supervisor()
    decision = sv.evaluate(run, elapsed_seconds=10)
    assert decision.action == "continue"


def test_supervisor_max_steps() -> None:
    run = RunRecord.from_spec(RunSpec(goal="exceed"))
    run.step = 60
    sv = Supervisor(SupervisorConfig(max_steps=50))
    decision = sv.evaluate(run)
    assert decision.action == "halt_blocked"


def test_supervisor_timeout() -> None:
    run = RunRecord.from_spec(RunSpec(goal="slow"))
    sv = Supervisor(SupervisorConfig(timeout_seconds=60))
    decision = sv.evaluate(run, elapsed_seconds=120)
    assert decision.action == "halt_timeout"


def test_supervisor_no_progress() -> None:
    run = RunRecord.from_spec(RunSpec(goal="stuck"))
    sv = Supervisor(SupervisorConfig(no_progress_threshold=3))
    decision = sv.evaluate(run, consecutive_no_progress=5)
    assert decision.action == "halt_blocked"


def test_supervisor_repeated_failures() -> None:
    run = RunRecord.from_spec(RunSpec(goal="failing"))
    sv = Supervisor(SupervisorConfig(repeated_failure_threshold=2))
    decision = sv.evaluate(run, consecutive_failures=3)
    assert decision.action == "halt_crashed"


def test_supervisor_cancel() -> None:
    run = RunRecord.from_spec(RunSpec(goal="cancel me"))
    sv = Supervisor()
    decision = sv.cancel(run)
    assert decision.action == "cancel"


# ── Signal Event Tests ────────────────────────────────────────


def test_signal_event_creation() -> None:
    sig = KernelSignalEvent(
        run_id="run-1",
        signal_type="pause",
        source="cli",
    )
    assert sig.signal_id
    assert sig.signal_type == "pause"
    assert sig.source == "cli"
