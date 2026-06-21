import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from loopos.review import ReviewCoordinator, ReviewStore
from loopos.tasks import TaskArtifactStore, TaskStore
from loopos.triggers import TriggerKernel
from loopos.worktree import WorktreeManager, WorktreeStore
from loopos.worktree.models import utc_now


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
            task_store = TaskStore(Path(tmp) / "tasks.json")
            task = TriggerKernel(task_store).fire("code-improvement")
            coordinator = ReviewCoordinator(ReviewStore(Path(tmp) / "reviews.json"))

            with self.assertRaises(ValueError):
                coordinator.start(task, producer="producer", verifier="verifier", reviewer="reviewer")

            record = WorktreeManager(WorktreeStore(Path(tmp) / "worktrees.json")).plan_for_task(task)
            task.worktree_id = record.id
            task_store.save(task)

            with self.assertRaises(ValueError):
                coordinator.start(task, producer="same", verifier="same", reviewer="same")

            review = coordinator.start(task, producer="producer", verifier="verifier", reviewer="reviewer")
            self.assertTrue(review.high_risk)
            self.assertEqual(review.status, "in_review")

            with self.assertRaises(ValueError):
                coordinator.approve(review.id, actor="reviewer")

            coordinator.verify(review.id, actor="verifier", note="pytest passed")
            approved = coordinator.approve(review.id, actor="reviewer")
            self.assertEqual(approved.status, "approved")

    def test_task_todos_and_artifacts_are_persistent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task_store = TaskStore(Path(tmp) / "tasks.json")
            artifact_store = TaskArtifactStore(Path(tmp) / "artifacts.json")
            task = TriggerKernel(task_store).fire("daily-maintenance")

            task = task_store.add_todo(task.id, "Run tests")
            todo_id = task.todos[0].id
            task = task_store.complete_todo(task.id, todo_id)
            report = artifact_store.create(
                task_id=task.id,
                artifact_type="report",
                title="Maintenance report",
                content="All checks passed.",
                ready=True,
            )

            self.assertEqual(task.todos[0].status, "done")
            self.assertEqual(artifact_store.list(task_id=task.id)[0].id, report.id)
            self.assertEqual(report.status, "ready")

    def test_worktree_materialization_plan_uses_git_worktree_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task = TriggerKernel(TaskStore(Path(tmp) / "tasks.json")).fire("code-improvement")
            manager = WorktreeManager(WorktreeStore(Path(tmp) / "worktrees.json"))
            record = manager.plan_for_task(task)

            plan = manager.materialization_plan(record, workspace=tmp)

            self.assertTrue(plan.dry_run)
            self.assertEqual(plan.commands[0].purpose, "create isolated git worktree")
            self.assertIn("worktree", plan.commands[0].cmd)
            self.assertTrue(plan.commands[0].requires_approval)

    def test_worktree_lease_expiry_and_cleanup_are_auditable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task = TriggerKernel(TaskStore(Path(tmp) / "tasks.json")).fire("code-improvement")
            store = WorktreeStore(Path(tmp) / "worktrees.json")
            manager = WorktreeManager(store)
            record = manager.plan_for_task(task, owner_id="producer-1", run_id="run-1")
            self.assertIsNotNone(record.lease_id)
            self.assertEqual(record.owner_id, "producer-1")
            record.lease_expires_at = utc_now() - timedelta(seconds=1)
            store.save(record)

            expired = manager.expire_leases()
            cleanup = manager.cleanup_plan(expired[0], workspace=tmp)
            self.assertEqual(expired[0].status, "stale")
            self.assertIn("worktree", cleanup.commands[0].cmd)
            self.assertEqual(cleanup.commands[0].risk, "high")


if __name__ == "__main__":
    unittest.main()
