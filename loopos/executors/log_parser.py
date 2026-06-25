"""Convert executor failures into LoopEngine review findings."""

from __future__ import annotations

from loopos.executors.result import TestRunResult
from loopos.loop_engine.models import ReviewFinding


class FailureLogParser:
    """Create actionable findings from a failed test run."""

    def to_findings(self, result: TestRunResult) -> list[ReviewFinding]:
        if result.status == "passed":
            return []
        evidence = list(result.failures)
        if result.stderr_ref:
            evidence.append(f"stderr_ref={result.stderr_ref}")
        if result.stdout_ref:
            evidence.append(f"stdout_ref={result.stdout_ref}")
        return [
            ReviewFinding(
                category="implementation_bug",
                severity="high",
                claim=f"Test command failed with exit_code={result.exit_code}.",
                evidence=evidence or [f"exit_code={result.exit_code}"],
                impact="The project is not ready to deliver until the failing test run is repaired.",
                recommended_fix="Use the failed test output to produce the next repair patch.",
                blocks_delivery=True,
            )
        ]


__all__ = ["FailureLogParser"]
