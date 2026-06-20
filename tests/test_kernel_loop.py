import tempfile
import unittest
from pathlib import Path

from loopos.kernel import KernelBoot, KernelConfig, KernelLoopEngine, RunSpec
from loopos.memory.repository import MemoryRepository


class KernelLoopTests(unittest.TestCase):
    def runtime(self, workspace: str, *, approve: bool = False):  # type: ignore[no-untyped-def]
        data_dir = Path(workspace) / ".loopos"
        return KernelBoot().start(
            KernelConfig(
                workspace=workspace,
                data_dir=str(data_dir),
                auto_approve_medium=approve,
            )
        )

    def test_hello_dry_run_has_required_sequence_and_no_side_effect(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = self.runtime(tmp)
            engine = KernelLoopEngine(runtime, memory_repository=MemoryRepository(Path(tmp) / ".loopos"))
            run = engine.run(
                RunSpec(
                    goal="创建 hello.py 并运行它",
                    workspace=tmp,
                    mode="dry_run",
                    max_steps=20,
                )
            )
            ops = [
                event.payload["op"]
                for event in runtime.trace_store.list(run.run_id)
                if event.kind == "instruction"
            ]
            self.assertEqual(
                ops,
                [
                    "GOAL.SET",
                    "GOAL.FINALIZE",
                    "CTX.COMPILE",
                    "PLAN.CREATE",
                    "FILE.WRITE",
                    "TERM.EXEC",
                    "EVAL.APPLY",
                    "PROGRESS.MEASURE",
                    "LOOP.HALT",
                ],
            )
            self.assertEqual(run.status, "succeeded")
            self.assertFalse((Path(tmp) / "hello.py").exists())

    def test_guarded_run_waits_then_resumes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = self.runtime(tmp)
            engine = KernelLoopEngine(runtime)
            waiting = engine.run(
                RunSpec(goal="创建 hello.py 并运行它", workspace=tmp, max_steps=20)
            )
            self.assertEqual(waiting.status, "waiting_approval")
            self.assertFalse((Path(tmp) / "hello.py").exists())

            resumed = engine.resume(waiting.run_id, approve=True)
            self.assertEqual(resumed.status, "waiting_approval")
            self.assertTrue((Path(tmp) / "hello.py").exists())

            completed = engine.resume(resumed.run_id, approve=True)
            self.assertEqual(completed.status, "succeeded")

    def test_medium_auto_approval_completes_guarded_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = self.runtime(tmp, approve=True)
            run = KernelLoopEngine(runtime).run(
                RunSpec(goal="创建 hello.py 并运行它", workspace=tmp, max_steps=20)
            )
            self.assertEqual(run.status, "succeeded")
            self.assertTrue((Path(tmp) / "hello.py").exists())

    def test_max_steps_halts_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = self.runtime(tmp)
            run = KernelLoopEngine(runtime).run(
                RunSpec(goal="demo", workspace=tmp, mode="dry_run", max_steps=1)
            )
            self.assertEqual(run.status, "failed")
            self.assertIn("scheduler.max_steps", run.errors)


if __name__ == "__main__":
    unittest.main()
