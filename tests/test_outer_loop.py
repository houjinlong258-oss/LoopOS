import tempfile
import unittest
from pathlib import Path

from loopos.review import ReviewCoordinator, ReviewStore
from loopos.tasks import TaskStore
from loopos.triggers import TriggerKernel
from loopos.worktree import WorktreeManager, WorktreeStore


class OuterLoopTests(unittest.TestCase):
    def test_trigger_creates_task_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tasks = TaskStore(Path(tmp) / "tasks.json")
            task = TriggerKernel(tasks).fire("daily-maintenance")

            self.assertEqual(task.source_trigger, "daily-maintenance")
            self.assertTrue(task.quick_win)
            self.assertEqual(task.status, "pending")
            next_task = tasks.next(quick_win=True)
            self.assertIsNotNone(next_task)
            assert next_task is not None
            self.assertEqual(next_task.id, task.id)

    def test_worktree_plan_isolated_branch_and_conflict_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task_store = TaskStore(Path(tmp) / "tasks.json")
            first = TriggerKernel(task_store).fire("code-improvement")
            second = TriggerKernel(task_store).fire("code-improvement")
            manager = WorktreeManager(WorktreeStore(Path(tmp) / "worktrees.json"))

            first_record = manager.plan_for_task(first, locked_paths=["loopos/core"])
            second_record = manager.plan_for_task(second, locked_paths=["loopos/core"])

            self.assertTrue(first_record.branch.startswith("codex/"))
            self.assertEqual(first_record.status, "planned")
            self.assertEqual(second_record.status, "conflict")
            self.assertEqual(second_record.conflict_task_ids, [first.id])

    def test_review_requires_role_separation_for_code_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task = TriggerKernel(TaskStore(Path(tmp) / "tasks.json")).fire("code-improvement")
            coordinator = ReviewCoordinator(ReviewStore(Path(tmp) / "reviews.json"))

            with self.assertRaises(ValueError):
                coordinator.start(task, producer="same", verifier="same", reviewer="same")

            review = coordinator.start(task, producer="producer", verifier="verifier", reviewer="reviewer")
            self.assertTrue(review.high_risk)
            self.assertEqual(review.status, "in_review")


if __name__ == "__main__":
    unittest.main()
