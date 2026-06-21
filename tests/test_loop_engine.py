import tempfile
import unittest
from pathlib import Path

from loopos.core.isa import make_instruction
from loopos.core.isa import Instruction
from loopos.core.loop_engine import LoopEngine
from loopos.core.state import LoopState


class NeverTerminatePolicy:
    def next_instruction(self, state: LoopState) -> Instruction:
        return make_instruction("PLAN", "keep_going", {"step": state.step_index})


class LoopEngineTests(unittest.TestCase):
    def test_success_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertWarns(DeprecationWarning):
                engine = LoopEngine.with_local_stores(Path(tmp))
            state = engine.run("demo", max_steps=3)
            self.assertEqual(state.status, "succeeded")
            self.assertEqual(state.step_index, 2)
            self.assertGreaterEqual(state.progress_score, 1.0)

    def test_max_steps_failure(self) -> None:
        with self.assertWarns(DeprecationWarning):
            engine = LoopEngine(policy=NeverTerminatePolicy())
        state = engine.run("never stop", max_steps=2)
        self.assertEqual(state.status, "failed")
        self.assertIn("max_steps exceeded", state.errors)


if __name__ == "__main__":
    unittest.main()
