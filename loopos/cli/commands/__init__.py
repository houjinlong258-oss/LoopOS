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
from loopos.computer_control import computer_command
from loopos.nodes.cli import nodes_command
from loopos.token_economy import token_command

# v0.3 commands.
from loopos.cli.commands.workbench import workbench_command
from loopos.cli.commands.adapters import adapters_command
from loopos.cli.commands.providers_runtime import (
    model_call_command,
    providers_runtime_command,
)
from loopos.cli.commands.opengod import opengod_command
from loopos.cli.commands.session import session_command
from loopos.cli.commands.readiness import readiness_command

# v0.4 commands
from loopos.cli.commands.imagine import imagine_command
from loopos.cli.commands.lail import lail_encode_command
from loopos.cli.commands.loop import (
    loop_artifacts_command,
    loop_deliver_command,
    loop_diff_command,
    loop_optimize_command,
    loop_repair_command,
    loop_replay_command,
    loop_review_command,
    loop_run_command,
    loop_status_command,
)
from loopos.cli.commands.locale import locale_command
from loopos.cli.commands.memory_v04 import memory_compile_command
from loopos.cli.commands.hookify import (
    hookify_list_command,
    hookify_enable_command,
    hookify_disable_command,
    hookify_test_command,
)

__all__ = [
    "ail_command",
    "code_command",
    "config_command",
    "computer_command",
    "db_command",
    "distill_command",
    "files_command",
    "fusion_command",
    "fusion_router_command",
    "gateway_command",
    "goal_command",
    "history_command",
    "kernel_command",
    "lail_command",
    "mad_dog_command",
    "memory_command",
    "mode_command",
    "models_command",
    "nodes_command",
    "parse_goal_options",
    "policy_command",
    "profile_command",
    "providers_command",
    "registry_command",
    "release_command",
    "replay_command",
    "repl_command",
    "resume_command",
    "review_command",
    "run_command",
    "search_command",
    "skills_command",
    "status_command",
    "index_command",
    "tasks_command",
    "token_command",
    "tools_command",
    "trace_command",
    "triggers_command",
    "worktrees_command",
    # v0.3
    "workbench_command",
    "adapters_command",
    "model_call_command",
    "providers_runtime_command",
    "opengod_command",
    "session_command",
    "readiness_command",
    # v0.4
    "imagine_command",
    "lail_encode_command",
    "loop_artifacts_command",
    "loop_deliver_command",
    "loop_diff_command",
    "loop_optimize_command",
    "loop_repair_command",
    "loop_replay_command",
    "loop_review_command",
    "loop_run_command",
    "loop_status_command",
    "locale_command",
    "memory_compile_command",
    "hookify_list_command",
    "hookify_enable_command",
    "hookify_disable_command",
    "hookify_test_command",
]
