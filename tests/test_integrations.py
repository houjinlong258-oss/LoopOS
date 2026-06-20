import tempfile
import unittest
from pathlib import Path

from loopos.integrations.langgraph_adapter import LangGraphAdapter
from loopos.integrations.letta_adapter import LettaAdapter
from loopos.integrations.openhands_adapter import OpenHandsAdapter
from loopos.integrations.projectmem_adapter import ProjectMemAdapter
from loopos.integrations.zep_adapter import ZepAdapter
from loopos.memory.belief_store import MemoryItem
from loopos.memory.event_log import EventLog


class IntegrationTests(unittest.TestCase):
    def test_openhands_fallback_file_ops(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adapter = OpenHandsAdapter(workspace=tmp)
            write = adapter.write_file("note.txt", "hello")
            self.assertTrue(write.success)
            read = adapter.read_file("note.txt")
            self.assertTrue(read.success)
            self.assertEqual(read.data["content"], "hello")

    def test_langgraph_fallback_runs(self) -> None:
        state = LangGraphAdapter().run_graph("demo", max_steps=3)
        self.assertEqual(state.status, "succeeded")

    def test_memory_adapter_shapes(self) -> None:
        item = MemoryItem(
            type="belief",
            content="remember this",
            confidence=0.9,
            source="test",
            tags=["x"],
        )
        self.assertEqual(LettaAdapter().to_memory_block(item)["value"], "remember this")
        self.assertEqual(ZepAdapter().to_session_memory(item, session_id="s")["session_id"], "s")

    def test_projectmem_event_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            event = EventLog(Path(tmp) / "events.jsonl").append("x", "run", 1, {})
            payload = ProjectMemAdapter().to_project_event(event)
            self.assertEqual(payload["run_id"], "run")


if __name__ == "__main__":
    unittest.main()
