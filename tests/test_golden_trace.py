import json
import tempfile
import unittest
from pathlib import Path

from loopos.core.loop_engine import LoopEngine
from loopos.kernel import KernelBoot, KernelConfig, KernelLoopEngine, RunSpec
from loopos.memory.event_log import EventLog


class GoldenTraceTests(unittest.TestCase):
    def test_demo_event_type_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            goal = Path("tests/fixtures/demo_goal.txt").read_text(encoding="utf-8").strip()
            with self.assertWarns(DeprecationWarning):
                engine = LoopEngine.with_local_stores(base)
            state = engine.run(goal, max_steps=3)
            self.assertEqual(state.status, "succeeded")

            events = EventLog(base / "events.jsonl").list(state.run_id)
            event_types = [event.type for event in events]
            expected = json.loads(
                Path("tests/golden/demo_event_types.json").read_text(encoding="utf-8")
            )
            self.assertEqual(event_types, expected)

    def test_kernel_hello_event_kind_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            runtime = KernelBoot().start(
                KernelConfig(workspace=tmp, data_dir=str(base / ".loopos"))
            )
            run = KernelLoopEngine(runtime).run(
                RunSpec(
                    goal="create hello.py and run it",
                    workspace=tmp,
                    mode="dry_run",
                )
            )
            kinds = [event.kind for event in runtime.trace_store.list(run.run_id)]
            expected = json.loads(
                Path("tests/golden/kernel_hello_event_kinds.json").read_text(encoding="utf-8")
            )
            self.assertEqual(run.status, "succeeded")
            self.assertEqual(kinds, expected)


if __name__ == "__main__":
    unittest.main()
