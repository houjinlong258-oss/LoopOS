import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def run_cli(
        self,
        *args: str,
        cwd: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "loopos.cli.app", *args],
            cwd=cwd or str(Path.cwd()),
            capture_output=True,
            text=True,
            timeout=20,
        )

    def test_help(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("LoopOS", result.stdout)

    def test_run_dry_run(self) -> None:
        result = self.run_cli("run", "demo", "--dry-run")
        self.assertEqual(result.returncode, 0)
        self.assertIn("EXEC_TERMINAL", result.stdout)

    def test_status_nonexistent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("status", "missing", "--data-dir", tmp)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Run not found", result.stderr)

    def test_skills_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("skills", "--data-dir", tmp)
            self.assertEqual(result.returncode, 0)
            self.assertIn("No skills stored", result.stdout)

    def test_config(self) -> None:
        result = self.run_cli("config")
        self.assertEqual(result.returncode, 0)
        self.assertIn('"llm": "mock-only"', result.stdout)


if __name__ == "__main__":
    unittest.main()
