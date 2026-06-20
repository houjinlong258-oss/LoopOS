import json
import tempfile
import unittest
from pathlib import Path

from loopos.core.loop_engine import LoopEngine
from loopos.memory.event_log import EventLog


class GoldenTraceTests(unittest.TestCase):
    def test_demo_event_type_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            goal = Path("tests/fixtures/demo_goal.txt").read_text(encoding="utf-8").strip()
            engine = LoopEngine.with_local_stores(base)
            state = engine.run(goal, max_steps=3)
            self.assertEqual(state.status, "succeeded")

            events = EventLog(base / "events.jsonl").list(state.run_id)
            event_types = [event.type for event in events]
            expected = json.loads(
                Path("tests/golden/demo_event_types.json").read_text(encoding="utf-8")
            )
            self.assertEqual(event_types, expected)


if __name__ == "__main__":
    unittest.main()
