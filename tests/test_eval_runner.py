import tempfile
import unittest
from pathlib import Path

from loopos.eval.metrics import compute_metrics
from loopos.eval.runner import EvalRunner


class EvalRunnerTests(unittest.TestCase):
    def test_load_and_run_tasks(self) -> None:
        runner = EvalRunner()
        tasks = runner.load_tasks("benchmarks/tasks")
        self.assertGreaterEqual(len(tasks), 2)
        with self.assertWarns(DeprecationWarning):
            report = runner.run_all(tasks)
        self.assertEqual(report["metrics"]["success_rate"], 1.0)
        self.assertGreaterEqual(report["metrics"]["command_count"], 2)

    def test_write_report(self) -> None:
        runner = EvalRunner()
        with tempfile.TemporaryDirectory() as tmp:
            path = runner.write_report({"ok": True}, Path(tmp) / "report.json")
            self.assertTrue(path.exists())

    def test_compute_metrics_empty(self) -> None:
        metrics = compute_metrics([])
        self.assertEqual(metrics.success_rate, 0.0)


if __name__ == "__main__":
    unittest.main()
