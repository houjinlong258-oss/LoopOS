"""Typed execution result models for the v0.4 full runtime."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


EXECUTOR_SOURCE = "loopos_real_executor"
COMMAND_RUNNER_SOURCE = "loopos_real_command_runner"


class ExecutionMode(BaseModel):
    """Execution permissions for real project-training adapters."""

    model_config = ConfigDict(extra="forbid")

    dry_run: bool = True
    sandbox: bool = True
    real_executor: bool = False
    allow_shell: bool = False
    allow_file_write: bool = False
    allow_network: bool = False
    sandbox_root: str | None = None


class CommandRequest(BaseModel):
    """A subprocess request captured before execution."""

    model_config = ConfigDict(extra="forbid")

    command: list[str]
    cwd: str
    timeout_seconds: int = Field(default=60, ge=1)
    env: dict[str, str] = Field(default_factory=dict)
    run_id: str
    iteration_id: str
    reason: str = ""
    expected_side_effects: list[str] = Field(default_factory=list)


class CommandResult(BaseModel):
    """A subprocess result with durable artifact references."""

    model_config = ConfigDict(extra="forbid")

    command: list[str]
    cwd: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    timed_out: bool = False
    artifacts: list[str] = Field(default_factory=list)
    source: str = COMMAND_RUNNER_SOURCE


class PatchRequest(BaseModel):
    """A unified-diff patch request."""

    model_config = ConfigDict(extra="forbid")

    patch: str
    cwd: str
    run_id: str
    iteration_id: str
    reason: str = ""


class PatchResult(BaseModel):
    """The result of applying a patch in a sandbox."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["applied", "failed", "dry_run"]
    changed_files: list[str] = Field(default_factory=list)
    diff_summary: str = ""
    error: str | None = None
    evidence: list[str] = Field(default_factory=list)


class TestRunResult(BaseModel):
    """A normalized test command result."""

    __test__ = False

    model_config = ConfigDict(extra="forbid")

    status: Literal["passed", "failed", "partial", "not_run"]
    exit_code: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    stdout_ref: str = ""
    stderr_ref: str = ""
    failures: list[str] = Field(default_factory=list)
    duration_ms: int = 0
    command_result: CommandResult | None = None


__all__ = [
    "COMMAND_RUNNER_SOURCE",
    "EXECUTOR_SOURCE",
    "CommandRequest",
    "CommandResult",
    "ExecutionMode",
    "PatchRequest",
    "PatchResult",
    "TestRunResult",
]
