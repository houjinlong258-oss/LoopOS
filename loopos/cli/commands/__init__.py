"""Modular CLI command implementations."""

from loopos.cli.commands.ail import ail_command
from loopos.cli.commands.config import config_command
from loopos.cli.commands.gateway import gateway_command
from loopos.cli.commands.goal import goal_command, parse_goal_options
from loopos.cli.commands.memory import memory_command, profile_command, skills_command
from loopos.cli.commands.models import models_command, providers_command
from loopos.cli.commands.policy import policy_command
from loopos.cli.commands.review import review_command
from loopos.cli.commands.tasks import tasks_command
from loopos.cli.commands.triggers import triggers_command
from loopos.cli.commands.worktrees import worktrees_command

__all__ = [
    "ail_command",
    "config_command",
    "gateway_command",
    "goal_command",
    "memory_command",
    "models_command",
    "parse_goal_options",
    "policy_command",
    "profile_command",
    "providers_command",
    "review_command",
    "skills_command",
    "tasks_command",
    "triggers_command",
    "worktrees_command",
]
