import tempfile
import unittest
from pathlib import Path

from loopos.core.state import LoopState
from loopos.memory.belief_store import MemoryItem
from loopos.memory.event_log import EventLog
from loopos.memory.proposals import MemoryProposal
from loopos.memory.repository import MemoryRepository


class MemoryRepositoryTests(unittest.TestCase):
    def test_sqlite_schema_bootstrap_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = MemoryRepository(tmp)
            repo.index.bootstrap()
            repo.index.bootstrap()
            self.assertTrue((Path(tmp) / "memory.sqlite3").exists())

    def test_reindex_from_jsonl_and_json_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = MemoryRepository(base)
            state = LoopState(goal="remember")
            repo.save_state(state)
            repo.events.append("observation", state.run_id, 1, {"command": "echo hello", "success": True})
            repo.beliefs.add(
                MemoryItem(
                    type="belief",
                    content="Use SQLite for memory indexes.",
                    confidence=0.9,
                    source="test",
                    tags=["sqlite"],
                    layer="semantic",
                )
            )

            rebuilt = MemoryRepository(base)
            counts = rebuilt.reindex()
            self.assertEqual(counts["runs"], 1)
            self.assertEqual(counts["events"], 1)
            self.assertEqual(counts["memory_items"], 1)
            self.assertEqual(rebuilt.retrieve(query_text="SQLite", tags=["sqlite"])[0].layer, "semantic")

    def test_proposal_accept_reject_and_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = MemoryRepository(tmp)
            proposal = MemoryProposal(
                proposed_item=MemoryItem(
                    type="preference",
                    layer="user_model",
                    scope="user",
                    content="User prefers concise output.",
                    confidence=0.8,
                    source="test",
                    tags=["style"],
                ),
                source="test",
                rationale="User asked for concise responses.",
            )
            repo.propose(proposal)
            self.assertEqual(len(repo.list_proposals(status="pending")), 1)
            accepted = repo.decide_proposal(proposal.id, "accepted", reasons=["test"])
            self.assertEqual(accepted.status, "accepted")
            self.assertEqual(len(repo.list_memory(layer="user_model")), 1)

            second = MemoryProposal(
                proposed_item=MemoryItem(
                    type="fact",
                    content="Rejected item.",
                    confidence=0.8,
                    source="test",
                ),
                source="test",
                rationale="reject path",
            )
            repo.propose(second)
            rejected = repo.decide_proposal(second.id, "rejected")
            self.assertEqual(rejected.status, "rejected")

            repo.set_profile("tone", "direct")
            self.assertEqual(repo.get_profile()["tone"], "direct")

    def test_proposal_for_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = MemoryRepository(tmp)
            event = EventLog(Path(tmp) / "events.jsonl").append("x", "run-id", 1, {})
            repo.index.upsert_event(event)
            proposal = repo.proposal_for_run("run-id")
            self.assertEqual(proposal.source_run_id, "run-id")


if __name__ == "__main__":
    unittest.main()
