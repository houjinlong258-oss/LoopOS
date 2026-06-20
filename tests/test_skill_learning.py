import sqlite3
import tempfile
import unittest
from pathlib import Path

from loopos.agents.skill_extractor import SkillExtractor
from loopos.kernel import RunRecord, TraceEvent
from loopos.memory.repository import MemoryRepository


def action_events(run_id: str) -> list[TraceEvent]:
    return [
        TraceEvent(
            run_id=run_id,
            step=1,
            kind="instruction",
            payload={"op": "FILE.READ", "args": {"path": "a.py"}},
        ),
        TraceEvent(
            run_id=run_id,
            step=2,
            kind="syscall",
            payload={"name": "terminal.exec", "input": {"cmd": "pytest -q"}},
        ),
    ]


class SkillLearningTests(unittest.TestCase):
    def test_extractor_requires_success_and_two_actions(self) -> None:
        extractor = SkillExtractor()
        failed = RunRecord(goal="fix", status="failed", phase="HALTED")
        with self.assertRaises(ValueError):
            extractor.extract(
                failed,
                action_events(failed.run_id),
                name="repair",
                description="repair tests",
                trigger_tags=["pytest"],
            )

        succeeded = RunRecord(goal="fix", status="succeeded", phase="HALTED")
        with self.assertRaises(ValueError):
            extractor.extract(
                succeeded,
                action_events(succeeded.run_id)[:1],
                name="repair",
                description="repair tests",
                trigger_tags=["pytest"],
            )

    def test_skill_commit_and_duplicate_merge_statistics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = MemoryRepository(tmp)
            extractor = SkillExtractor()
            first_run = RunRecord(goal="fix", status="succeeded", phase="HALTED")
            first = extractor.extract(
                first_run,
                action_events(first_run.run_id),
                name="pytest repair",
                description="repair pytest failures",
                trigger_tags=["pytest"],
            )
            repo.propose_skill(first)
            accepted = repo.commit_skill_proposal(first.id)
            self.assertEqual(accepted.status, "accepted")

            second_run = RunRecord(goal="fix again", status="succeeded", phase="HALTED")
            second = extractor.extract(
                second_run,
                action_events(second_run.run_id),
                name="pytest repair",
                description="repair pytest failures",
                trigger_tags=["pytest"],
            )
            repo.propose_skill(second)
            merged = repo.commit_skill_proposal(second.id)
            skills = repo.skills.list()
            self.assertEqual(merged.status, "merged")
            self.assertEqual(len(skills), 1)
            self.assertEqual(skills[0].success_count, 2)
            self.assertEqual(set(skills[0].source_runs), {first_run.run_id, second_run.run_id})

    def test_sqlite_migration_adds_trace_and_skill_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = MemoryRepository(tmp)
            repo.index.bootstrap()
            connection = sqlite3.connect(Path(tmp) / "memory.sqlite3")
            try:
                event_columns = {row[1] for row in connection.execute("PRAGMA table_info(events)")}
                skill_columns = {row[1] for row in connection.execute("PRAGMA table_info(skills)")}
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
            finally:
                connection.close()
            self.assertIn("policy_decision_id", event_columns)
            self.assertIn("success_rate", skill_columns)
            self.assertIn("skill_proposals", tables)


if __name__ == "__main__":
    unittest.main()
