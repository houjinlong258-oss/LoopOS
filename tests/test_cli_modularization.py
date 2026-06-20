import tempfile
import unittest
from pathlib import Path

from loopos.cli import app as cli_app
from loopos.cli.commands.gateway import gateway_command
from loopos.cli.commands.models import models_command, providers_command
from loopos.cli.commands.review import review_command
from loopos.cli.commands.tasks import tasks_command
from loopos.cli.commands.triggers import triggers_command
from loopos.cli.commands.worktrees import worktrees_command
from loopos.cli.context import data_paths


class CliModularizationTests(unittest.TestCase):
    def test_app_exports_modular_command_functions(self) -> None:
        self.assertIs(cli_app.tasks_command, tasks_command)
        self.assertIs(cli_app.triggers_command, triggers_command)
        self.assertIs(cli_app.worktrees_command, worktrees_command)
        self.assertIs(cli_app.review_command, review_command)
        self.assertIs(cli_app.providers_command, providers_command)
        self.assertIs(cli_app.models_command, models_command)
        self.assertIs(cli_app.gateway_command, gateway_command)

    def test_shared_data_paths_preserve_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = data_paths(tmp)

            self.assertEqual(paths["base"], Path(tmp))
            self.assertEqual(paths["runs"], Path(tmp) / "runs")
            self.assertEqual(paths["gateway_approvals"], Path(tmp) / "gateway_approvals.json")
            self.assertEqual(cli_app._paths(tmp), paths)


if __name__ == "__main__":
    unittest.main()
