import tempfile
import unittest
from pathlib import Path

from loopos.cli import app as cli_app
from loopos.cli.commands.ail import ail_command
from loopos.cli.commands.config import config_command
from loopos.cli.commands.gateway import gateway_command
from loopos.cli.commands.goal import goal_command, parse_goal_options
from loopos.cli.commands.memory import memory_command, profile_command, skills_command
from loopos.cli.commands.models import models_command, providers_command
from loopos.cli.commands.policy import policy_command
from loopos.cli.commands.review import review_command
from loopos.cli.commands.runtime import (
    history_command,
    replay_command,
    resume_command,
    run_command,
    status_command,
    tools_command,
    trace_command,
)
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
        self.assertIs(cli_app.goal_command, goal_command)
        self.assertIs(cli_app.memory_command, memory_command)
        self.assertIs(cli_app.profile_command, profile_command)
        self.assertIs(cli_app.skills_command, skills_command)
        self.assertIs(cli_app.policy_command, policy_command)
        self.assertIs(cli_app.ail_command, ail_command)
        self.assertIs(cli_app.config_command, config_command)
        self.assertIs(cli_app.run_command, run_command)
        self.assertIs(cli_app.resume_command, resume_command)
        self.assertIs(cli_app.status_command, status_command)
        self.assertIs(cli_app.history_command, history_command)
        self.assertIs(cli_app.trace_command, trace_command)
        self.assertIs(cli_app.replay_command, replay_command)
        self.assertIs(cli_app.tools_command, tools_command)
        self.assertIs(getattr(cli_app, "_parse_goal_options"), parse_goal_options)

    def test_shared_data_paths_preserve_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = data_paths(tmp)

            self.assertEqual(paths["base"], Path(tmp))
            self.assertEqual(paths["runs"], Path(tmp) / "runs")
            self.assertEqual(paths["gateway_approvals"], Path(tmp) / "gateway_approvals.json")
            self.assertEqual(cli_app._paths(tmp), paths)


if __name__ == "__main__":
    unittest.main()
