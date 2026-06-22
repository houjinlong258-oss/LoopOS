"""Modular CLI command implementations."""

from loopos.cli.commands.ail import ail_command
from loopos.cli.commands.code import code_command
from loopos.cli.commands.config import config_command
from loopos.cli.commands.data_guard import db_command
from loopos.cli.commands.distill import distill_command
from loopos.cli.commands.ecosystem import mode_command, registry_command
from loopos.cli.commands.fusion import fusion_command
from loopos.cli.commands.fusion_router import fusion_router_command
from loopos.cli.commands.gateway import gateway_command
from loopos.cli.commands.goal import goal_command, parse_goal_options
from loopos.cli.commands.kernel_cli import kernel_command
from loopos.cli.commands.mad_dog import mad_dog_command
from loopos.cli.commands.memory import memory_command, profile_command, skills_command
from loopos.cli.commands.local_intel import files_command, index_command, search_command
from loopos.cli.commands.models import models_command, providers_command
from loopos.cli.commands.policy import policy_command
from loopos.cli.commands.release_cli import release_command
from loopos.cli.commands.review import review_command
from loopos.cli.commands.runtime import (
    history_command,
    replay_command,
    repl_command,
    resume_command,
    run_command,
    status_command,
    tools_command,
    trace_command,
)
from loopos.cli.commands.tasks import tasks_command
from loopos.cli.commands.triggers import triggers_command
from loopos.cli.commands.worktrees import worktrees_command

__all__ = [
    "ail_command",
    "code_command",
    "config_command",
    "db_command",
    "distill_command",
    "files_command",
    "fusion_command",
    "fusion_router_command",
    "gateway_command",
    "goal_command",
    "kernel_command",
    "mad_dog_command",
    "memory_command",
    "mode_command",
    "models_command",
    "parse_goal_options",
    "policy_command",
    "profile_command",
    "release_command",
    "registry_command",
    "search_command",
    "providers_command",
    "review_command",
    "history_command",
    "replay_command",
    "repl_command",
    "resume_command",
    "run_command",
    "status_command",
    "index_command",
    "skills_command",
    "tasks_command",
    "tools_command",
    "trace_command",
    "triggers_command",
    "worktrees_command",
]
