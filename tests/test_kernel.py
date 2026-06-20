import json
import tempfile
import unittest
from pathlib import Path

from loopos.core.state import LoopState
from loopos.kernel import (
    KernelBoot,
    KernelBootError,
    KernelConfig,
    KernelSignal,
    KernelStateMachine,
    LoopScheduler,
    RunManager,
    RunRecord,
    RunSpec,
    SchedulerInput,
    TransitionEngine,
)


class KernelProcessTests(unittest.TestCase):
    def test_run_manager_creates_and_loads_versioned_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manager = RunManager(tmp)
            run = manager.create(RunSpec(goal="demo", workspace=tmp, max_steps=4))

            loaded = manager.load(run.run_id)
            self.assertEqual(loaded.schema_version, 2)
            self.assertEqual(loaded.max_steps, 4)
            self.assertEqual(loaded.status, "pending")

    def test_run_manager_reads_legacy_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            legacy = LoopState(goal="legacy", status="running", step_index=2)
            path = Path(tmp) / f"{legacy.run_id}.json"
            path.write_text(legacy.model_dump_json(), encoding="utf-8")

            loaded = RunManager(tmp).load(legacy.run_id)
            self.assertEqual(loaded.run_id, legacy.run_id)
            self.assertTrue(loaded.metadata["legacy_record"])
            self.assertEqual(loaded.step, 2)

    def test_run_record_json_roundtrip(self) -> None:
        run = RunRecord.from_spec(RunSpec(goal="roundtrip"))
        decoded = RunRecord.model_validate(json.loads(run.model_dump_json()))
        self.assertEqual(decoded.run_id, run.run_id)

    def test_boot_registers_kernel_services(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = KernelBoot().start(
                KernelConfig(workspace=tmp, data_dir=str(Path(tmp) / ".loopos"))
            )
            self.assertEqual(len(runtime.syscall_router.registry.list()), 5)
            self.assertTrue((Path(tmp) / ".loopos" / "runs").is_dir())

    def test_boot_rejects_missing_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(KernelBootError):
                KernelBoot().start(KernelConfig(workspace=str(Path(tmp) / "missing")))


class KernelSchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scheduler = LoopScheduler()

    def test_scheduler_precedence(self) -> None:
        blocked = self.scheduler.decide(SchedulerInput(step=0, max_steps=3, policy_allowed=False))
        waiting = self.scheduler.decide(SchedulerInput(step=0, max_steps=3, approval_required=True))
        success = self.scheduler.decide(SchedulerInput(step=1, max_steps=3, evaluation_success=True))
        repair = self.scheduler.decide(
            SchedulerInput(step=1, max_steps=3, evaluation_failed=True, repairable=True)
        )
        replan = self.scheduler.decide(SchedulerInput(step=1, max_steps=3, no_progress=True))
        bounded = self.scheduler.decide(SchedulerInput(step=3, max_steps=3))

        self.assertEqual(blocked.action, "halt_blocked")
        self.assertEqual(waiting.action, "wait_approval")
        self.assertEqual(success.action, "halt_succeeded")
        self.assertEqual(repair.action, "repair")
        self.assertEqual(replan.action, "replan")
        self.assertEqual(bounded.action, "halt_failed")

    def test_cancel_signal_wins(self) -> None:
        decision = self.scheduler.decide(
            SchedulerInput(step=0, max_steps=3, signal=KernelSignal.CANCEL)
        )
        self.assertEqual(decision.action, "halt_cancelled")

    def test_state_machine_waits_for_approval(self) -> None:
        run = RunRecord(goal="approval", status="running", phase="EXECUTING")
        decision = self.scheduler.decide(
            SchedulerInput(step=0, max_steps=3, approval_required=True)
        )
        KernelStateMachine().apply_schedule(run, decision)
        self.assertEqual(run.status, "waiting_approval")
        self.assertEqual(run.phase, "WAITING_APPROVAL")

    def test_invalid_transition_is_rejected(self) -> None:
        run = RunRecord(goal="done", status="succeeded", phase="HALTED")
        with self.assertRaises(ValueError):
            TransitionEngine().apply(run, "running", "EXECUTING")


if __name__ == "__main__":
    unittest.main()
