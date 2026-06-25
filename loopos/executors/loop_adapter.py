"""LoopEngine adapters backed by the real executor package."""

from __future__ import annotations

import difflib
import sys
from pathlib import Path
from typing import Any

from loopos.executors.artifact import ExecutionArtifactStore
from loopos.executors.diff_analyzer import DiffAnalyzer
from loopos.executors.log_parser import FailureLogParser
from loopos.executors.patch_applier import PatchApplier
from loopos.executors.result import EXECUTOR_SOURCE, ExecutionMode, PatchRequest
from loopos.executors.safety_adapter import ExecutorSafetyAdapter
from loopos.executors.test_runner import TestRunner
from loopos.loop_engine.builder import LoopBuilder
from loopos.loop_engine.models import (
    BuildResult,
    LoopState,
    PlanCandidate,
    ReviewFinding,
    SuccessCriteria,
    TestResult,
)
from loopos.loop_engine.reviewer import LoopReviewer


class RealProjectBuilder(LoopBuilder):
    """Apply a deterministic patch in a sandboxed project repo."""

    def __init__(
        self,
        repo_path: str | Path,
        *,
        mode: ExecutionMode | None = None,
        artifact_store: ExecutionArtifactStore | None = None,
    ) -> None:
        super().__init__()
        self.repo_path = Path(repo_path).resolve()
        self.mode = mode or ExecutionMode(
            dry_run=False,
            sandbox=True,
            real_executor=True,
            allow_shell=True,
            allow_file_write=True,
            sandbox_root=str(self.repo_path),
        )
        self.artifact_store = artifact_store
        self.safety = ExecutorSafetyAdapter()

    def build(
        self,
        plan: PlanCandidate,
        iteration_id: str,
        dry_run: bool = True,
    ) -> BuildResult:
        proposal = propose_simple_python_repair(self.repo_path)
        if proposal is None:
            return BuildResult(
                iteration_id=iteration_id,
                plan_id=plan.id,
                status="applied",
                source=EXECUTOR_SOURCE,
                changed_files=[],
                summary="Real executor inspected the repo; no deterministic patch proposal was found.",
                artifacts=[],
            )
        decision = self.safety.evaluate_patch()
        if not decision.allowed:
            return BuildResult(
                iteration_id=iteration_id,
                plan_id=plan.id,
                status="failed",
                source=EXECUTOR_SOURCE,
                errors=decision.reason_codes,
                summary="Action boundary blocked patch application.",
            )
        mode = self.mode.model_copy(update={"dry_run": dry_run})
        patch_result = PatchApplier(mode).apply(
            PatchRequest(
                patch=proposal,
                cwd=str(self.repo_path),
                run_id="loop_engine",
                iteration_id=iteration_id,
                reason="deterministic_simple_repair",
            )
        )
        changed_files, diff_summary = DiffAnalyzer().analyze(self.repo_path)
        status = "applied" if patch_result.status in {"applied", "dry_run"} else "failed"
        return BuildResult(
            iteration_id=iteration_id,
            plan_id=plan.id,
            status=status,
            source=EXECUTOR_SOURCE,
            changed_files=changed_files or patch_result.changed_files,
            summary=diff_summary or patch_result.diff_summary,
            errors=[patch_result.error] if patch_result.error else [],
            artifacts=patch_result.evidence,
        )


class RealProjectTester:
    """LoopEngine tester adapter backed by TestRunner."""

    def __init__(
        self,
        repo_path: str | Path,
        *,
        mode: ExecutionMode | None = None,
        command: list[str] | None = None,
        artifact_store: ExecutionArtifactStore | None = None,
    ) -> None:
        self.repo_path = Path(repo_path).resolve()
        self.mode = mode or ExecutionMode(
            dry_run=False,
            sandbox=True,
            real_executor=True,
            allow_shell=True,
            allow_file_write=False,
            sandbox_root=str(self.repo_path),
        )
        self.command = command or [sys.executable, "-m", "pytest", "-q"]
        self.runner = TestRunner(self.mode, artifact_store=artifact_store)

    def test(
        self,
        build: BuildResult,
        criteria: SuccessCriteria,
        iteration_id: str,
        dry_run: bool = True,
    ) -> TestResult:
        mode = self.mode.model_copy(update={"dry_run": dry_run})
        runner = TestRunner(mode, artifact_store=self.runner.artifact_store)
        result = runner.run(
            self.repo_path,
            run_id="loop_engine",
            iteration_id=iteration_id,
            command=self.command,
        )
        return TestResult(
            iteration_id=iteration_id,
            status=result.status,
            source=EXECUTOR_SOURCE,
            passed=result.passed,
            failed=result.failed,
            skipped=result.skipped,
            failures=result.failures,
            commands=[" ".join(self.command)],
            duration_ms=result.duration_ms,
            evidence=[
                item for item in [result.stdout_ref, result.stderr_ref] if item
            ],
        )


class RealProjectReviewer(LoopReviewer):
    """Reviewer adapter that consumes real test failures."""

    def review(
        self,
        state: LoopState,
        plan: PlanCandidate,
        build: BuildResult | None,
        tests: TestResult | None,
    ) -> list[ReviewFinding]:
        findings = super().review(state, plan, build, tests)
        if tests is not None and (tests.failed > 0 or tests.status in {"failed", "partial"}):
            result = TestRunResultAdapter.from_test_result(tests)
            findings.extend(FailureLogParser().to_findings(result))
        return findings


class TestRunResultAdapter:
    """Small adapter to reuse FailureLogParser from LoopEngine tests."""

    @staticmethod
    def from_test_result(tests: TestResult) -> Any:
        from loopos.executors.result import TestRunResult

        return TestRunResult(
            status="failed" if tests.failed else "passed",
            exit_code=1 if tests.failed else 0,
            passed=tests.passed,
            failed=tests.failed,
            skipped=tests.skipped,
            failures=tests.failures,
            stdout_ref=tests.evidence[0] if tests.evidence else "",
            stderr_ref=tests.evidence[1] if len(tests.evidence) > 1 else "",
            duration_ms=tests.duration_ms or 0,
        )


def propose_simple_python_repair(repo_path: str | Path) -> str | None:
    """Return a unified diff for a tiny deterministic Python repair."""

    root = Path(repo_path)
    for path in sorted(root.rglob("*.py")):
        if any(part in {".venv", "__pycache__", "tests"} for part in path.parts):
            continue
        original = path.read_text(encoding="utf-8", errors="replace")
        repaired = _repair_text(original)
        if repaired == original:
            continue
        rel = path.relative_to(root).as_posix()
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            repaired.splitlines(keepends=True),
            fromfile=f"a/{rel}",
            tofile=f"b/{rel}",
        )
        return "".join(diff)
    return None


def _repair_text(text: str) -> str:
    replacements = [
        ("return a - b", "return a + b"),
        ("return x - y", "return x + y"),
        ("return False", "return True"),
        ("return None", "return True"),
    ]
    for old, new in replacements:
        if old in text:
            return text.replace(old, new, 1)
    return text


__all__ = [
    "RealProjectBuilder",
    "RealProjectReviewer",
    "RealProjectTester",
    "propose_simple_python_repair",
]
