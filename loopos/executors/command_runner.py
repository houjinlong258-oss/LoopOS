"""Subprocess runner used by real executor adapters."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from loopos.executors.artifact import ExecutionArtifactStore
from loopos.executors.result import (
    COMMAND_RUNNER_SOURCE,
    CommandRequest,
    CommandResult,
    ExecutionMode,
)
from loopos.executors.sandbox import SandboxGuard, SandboxViolation
from loopos.output_compaction import OutputCompactor


class CommandRunner:
    """Run explicit argv commands and capture stdout/stderr/exit code."""

    def __init__(
        self,
        mode: ExecutionMode | None = None,
        *,
        artifact_store: ExecutionArtifactStore | None = None,
    ) -> None:
        self.mode = mode or ExecutionMode()
        self.artifact_store = artifact_store
        self._timeout_tripped = False

    @property
    def timeout_tripped(self) -> bool:
        return self._timeout_tripped

    def run(self, request: CommandRequest) -> CommandResult:
        if self._timeout_tripped:
            return CommandResult(
                command=request.command,
                cwd=request.cwd,
                exit_code=124,
                stderr="previous command timed out; follow-up command suppressed",
                timed_out=True,
                source="loopos_executor_skipped_after_timeout",
            )
        if self.mode.dry_run or not self.mode.allow_shell:
            return CommandResult(
                command=request.command,
                cwd=request.cwd,
                exit_code=0,
                stdout="dry_run: command not executed",
                source="loopos_executor_dry_run",
            )
        cwd = self._resolve_cwd(request.cwd)
        env = os.environ.copy()
        env.update(request.env)
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                request.command,
                cwd=str(cwd),
                env=env,
                text=True,
                capture_output=True,
                timeout=request.timeout_seconds,
                check=False,
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            result = CommandResult(
                command=request.command,
                cwd=str(cwd),
                exit_code=int(completed.returncode),
                stdout=completed.stdout,
                stderr=completed.stderr,
                duration_ms=duration_ms,
                timed_out=False,
                source=COMMAND_RUNNER_SOURCE,
            )
        except subprocess.TimeoutExpired as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            self._timeout_tripped = True
            result = CommandResult(
                command=request.command,
                cwd=str(cwd),
                exit_code=124,
                stdout=_decode_timeout_stream(exc.stdout),
                stderr=_decode_timeout_stream(exc.stderr) or "command timed out",
                duration_ms=duration_ms,
                timed_out=True,
                source=COMMAND_RUNNER_SOURCE,
            )
        return self._with_artifacts(result, request)

    def _resolve_cwd(self, cwd: str) -> Path:
        root = self.mode.sandbox_root if self.mode.sandbox else None
        try:
            return SandboxGuard(root).ensure_inside(cwd)
        except SandboxViolation:
            raise

    def _with_artifacts(self, result: CommandResult, request: CommandRequest) -> CommandResult:
        if self.artifact_store is None:
            return result
        compactor = OutputCompactor()
        refs = [
            self.artifact_store.write_text(
                run_id=request.run_id,
                iteration_id=request.iteration_id,
                name="stdout.raw.txt",
                text=result.stdout,
            ),
            self.artifact_store.write_text(
                run_id=request.run_id,
                iteration_id=request.iteration_id,
                name="stderr.raw.txt",
                text=result.stderr,
            ),
            self.artifact_store.write_text(
                run_id=request.run_id,
                iteration_id=request.iteration_id,
                name="stdout.compacted.txt",
                text=compactor.compact(result.stdout, exit_code=result.exit_code).summary,
            ),
            self.artifact_store.write_text(
                run_id=request.run_id,
                iteration_id=request.iteration_id,
                name="stderr.compacted.txt",
                text=compactor.compact(result.stderr, exit_code=result.exit_code).summary,
            ),
        ]
        return result.model_copy(update={"artifacts": refs})


def _decode_timeout_stream(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


__all__ = ["CommandRunner"]
