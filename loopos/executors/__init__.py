"""Real Project Training executor runtime."""

from __future__ import annotations

from loopos.executors.artifact import ExecutionArtifactStore
from loopos.executors.base import PatchExecutor, PatchProposal, ProjectTestExecutor
from loopos.executors.command_runner import CommandRunner
from loopos.executors.diff_analyzer import DiffAnalyzer
from loopos.executors.log_parser import FailureLogParser
from loopos.executors.loop_adapter import (
    RealProjectBuilder,
    RealProjectReviewer,
    RealProjectTester,
    propose_simple_python_repair,
)
from loopos.executors.patch_applier import PatchApplier, changed_files_from_patch
from loopos.executors.repo_inspector import RepoInspector
from loopos.executors.result import (
    COMMAND_RUNNER_SOURCE,
    EXECUTOR_SOURCE,
    CommandRequest,
    CommandResult,
    ExecutionMode,
    PatchRequest,
    PatchResult,
    TestRunResult,
)
from loopos.executors.safety_adapter import ExecutorSafetyAdapter
from loopos.executors.sandbox import SandboxGuard, SandboxViolation, copy_to_temp_sandbox
from loopos.executors.test_runner import TestRunner

__all__ = [
    "COMMAND_RUNNER_SOURCE",
    "EXECUTOR_SOURCE",
    "CommandRequest",
    "CommandResult",
    "CommandRunner",
    "DiffAnalyzer",
    "ExecutionArtifactStore",
    "ExecutionMode",
    "ExecutorSafetyAdapter",
    "FailureLogParser",
    "PatchApplier",
    "PatchExecutor",
    "PatchProposal",
    "PatchRequest",
    "PatchResult",
    "ProjectTestExecutor",
    "RealProjectBuilder",
    "RealProjectReviewer",
    "RealProjectTester",
    "RepoInspector",
    "SandboxGuard",
    "SandboxViolation",
    "TestRunResult",
    "TestRunner",
    "changed_files_from_patch",
    "copy_to_temp_sandbox",
    "propose_simple_python_repair",
]
