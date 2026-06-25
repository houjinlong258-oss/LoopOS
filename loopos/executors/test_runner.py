"""Test command runner and pytest output parser."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from loopos.executors.artifact import ExecutionArtifactStore
from loopos.executors.command_runner import CommandRunner
from loopos.executors.result import CommandRequest, ExecutionMode, TestRunResult


class TestRunner:
    """Run a test command and normalize the result."""

    __test__ = False

    def __init__(
        self,
        mode: ExecutionMode | None = None,
        *,
        artifact_store: ExecutionArtifactStore | None = None,
    ) -> None:
        self.mode = mode or ExecutionMode()
        self.artifact_store = artifact_store
        self.command_runner = CommandRunner(self.mode, artifact_store=artifact_store)

    def run(
        self,
        cwd: str | Path,
        *,
        run_id: str,
        iteration_id: str,
        command: list[str] | None = None,
        timeout_seconds: int = 120,
    ) -> TestRunResult:
        cmd = command or [sys.executable, "-m", "pytest", "-q"]
        result = self.command_runner.run(
            CommandRequest(
                command=cmd,
                cwd=str(cwd),
                timeout_seconds=timeout_seconds,
                run_id=run_id,
                iteration_id=iteration_id,
                reason="project_training_test_run",
            )
        )
        passed, failed, skipped = parse_pytest_counts(result.stdout + "\n" + result.stderr)
        failures = extract_failure_lines(result.stdout + "\n" + result.stderr)
        if result.exit_code != 0 and failed == 0:
            failed = 1
        if result.exit_code == 0 and not result.timed_out:
            status = "passed"
        elif result.exit_code == 124 or result.timed_out:
            status = "failed"
            failures = failures or ["test command timed out"]
        elif passed > 0 and failed > 0:
            status = "partial"
        else:
            status = "failed"
        stdout_ref = _artifact_ref(result.artifacts, "stdout.raw.txt")
        stderr_ref = _artifact_ref(result.artifacts, "stderr.raw.txt")
        return TestRunResult(
            status=status,
            exit_code=result.exit_code,
            passed=passed,
            failed=failed,
            skipped=skipped,
            stdout_ref=stdout_ref,
            stderr_ref=stderr_ref,
            failures=failures,
            duration_ms=result.duration_ms,
            command_result=result,
        )


def parse_pytest_counts(text: str) -> tuple[int, int, int]:
    """Parse common pytest summary lines."""

    passed = failed = skipped = 0
    patterns = {
        "passed": r"(\d+)\s+passed",
        "failed": r"(\d+)\s+failed",
        "skipped": r"(\d+)\s+skipped",
    }
    for name, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            if name == "passed":
                passed = int(match.group(1))
            elif name == "failed":
                failed = int(match.group(1))
            else:
                skipped = int(match.group(1))
    return passed, failed, skipped


def extract_failure_lines(text: str, *, limit: int = 12) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("E   ", "FAILED ", "ERROR ")) or "AssertionError" in stripped:
            lines.append(stripped)
        if len(lines) >= limit:
            break
    return lines


def _artifact_ref(artifacts: list[str], suffix: str) -> str:
    for ref in artifacts:
        if ref.endswith(suffix):
            return ref
    return ""


__all__ = ["TestRunner", "extract_failure_lines", "parse_pytest_counts"]
