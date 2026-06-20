import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from loopos.core.isa import make_instruction


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

    def test_memory_reindex_and_search(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reindex = self.run_cli("memory", "reindex", "--data-dir", tmp)
            self.assertEqual(reindex.returncode, 0)
            self.assertIn('"memory_items": 0', reindex.stdout)

            search = self.run_cli("memory", "search", "missing", "--data-dir", tmp)
            self.assertEqual(search.returncode, 0)
            self.assertIn("[]", search.stdout)

    def test_memory_propose_accept_reject(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = self.run_cli("run", "demo", "--max-steps", "3", "--data-dir", tmp)
            self.assertEqual(run.returncode, 0)
            run_files = list((Path(tmp) / "runs").glob("*.json"))
            self.assertEqual(len(run_files), 1)
            run_id = run_files[0].stem

            propose = self.run_cli("memory", "propose", "--from-run", run_id, "--data-dir", tmp)
            self.assertEqual(propose.returncode, 0)
            proposal_id = propose.stdout.strip().split()[-1]

            review = self.run_cli("memory", "review", "--data-dir", tmp)
            self.assertEqual(review.returncode, 0)
            self.assertIn(proposal_id, review.stdout)

            accept = self.run_cli("memory", "accept", proposal_id, "--data-dir", tmp)
            self.assertEqual(accept.returncode, 0)
            self.assertIn("accepted", accept.stdout)

    def test_profile_show_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            show = self.run_cli("profile", "show", "--data-dir", tmp)
            self.assertEqual(show.returncode, 0)
            self.assertIn("No user profile", show.stdout)

            set_result = self.run_cli("profile", "set", "tone", "direct", "--data-dir", tmp)
            self.assertEqual(set_result.returncode, 0)

            show_again = self.run_cli("profile", "show", "--data-dir", tmp)
            self.assertEqual(show_again.returncode, 0)
            self.assertIn('"tone": "direct"', show_again.stdout)

    def test_policy_list_and_check(self) -> None:
        list_result = self.run_cli("policy", "list")
        self.assertEqual(list_result.returncode, 0)
        self.assertIn("terminal.block.destructive_patterns", list_result.stdout)

        check = self.run_cli(
            "policy",
            "check",
            "--scope",
            "terminal.execute",
            "--input",
            '{"cmd":"rm -rf tmp"}',
        )
        self.assertEqual(check.returncode, 2)
        self.assertIn('"action": "deny"', check.stdout)

    def test_policy_show(self) -> None:
        result = self.run_cli("policy", "show", "terminal.block.destructive_patterns")
        self.assertEqual(result.returncode, 0)
        self.assertIn('"scope": "terminal.execute"', result.stdout)

    def test_ail_validate_and_inspect(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "instruction.json"
            path.write_text(
                make_instruction(
                    "EXEC_TERMINAL",
                    "cli_validate",
                    {"cmd": "echo hi"},
                ).model_dump_json(),
                encoding="utf-8",
            )
            validate = self.run_cli("ail", "validate", str(path))
            self.assertEqual(validate.returncode, 0)
            self.assertIn("valid AIL instruction", validate.stdout)

            inspect = self.run_cli("ail", "inspect", str(path))
            self.assertEqual(inspect.returncode, 0)
            self.assertIn('"policy_scope": "terminal.execute"', inspect.stdout)


if __name__ == "__main__":
    unittest.main()
