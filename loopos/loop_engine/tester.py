"""Loop tester: produces a ``TestResult`` for a build.

In v0.4.0 the tester is **simulated** by default. It produces a
``TestResult`` whose ``status`` is one of:

* ``"simulated"`` — no real tests were executed.
* ``"passed"`` — a real test runner reported all-pass (only when a
  ``test_fn`` is plugged in).

The simulated path is deterministic: the same ``BuildResult`` always
produces the same ``TestResult`` for the default tester. Real
testers can be plugged in by setting ``test_fn``.
"""

from __future__ import annotations

from typing import Callable

from loopos.loop_engine.models import (
    BuildResult,
    SuccessCriteria,
    TestResult,
)


class LoopTester:
    """Emit a ``TestResult`` for a build."""

    def __init__(
        self,
        test_fn: Callable[[BuildResult, SuccessCriteria], TestResult] | None = None,
    ) -> None:
        self._test_fn = test_fn

    def test(
        self,
        build: BuildResult,
        criteria: SuccessCriteria,
        iteration_id: str,
        dry_run: bool = True,
    ) -> TestResult:
        # If a custom test_fn is plugged in, it is the source of
        # truth for the iteration's test result. The dry_run flag
        # only affects the default simulated implementation.
        if self._test_fn is not None:
            return self._test_fn(build, criteria)
        if not dry_run:
            return self._simulate(build, criteria, iteration_id)
        return self._simulate(build, criteria, iteration_id)

    def _simulate(
        self,
        build: BuildResult,
        criteria: SuccessCriteria,
        iteration_id: str,
    ) -> TestResult:
        # Default simulated result: one passing test per required criterion.
        required = [c for c in criteria.items if c.required]
        passed = len(required)
        failed = 0
        skipped = 0
        return TestResult(
            iteration_id=iteration_id,
            status="simulated",
            passed=passed,
            failed=failed,
            skipped=skipped,
            failures=[],
            commands=[],
            duration_ms=None,
            evidence=[
                f"simulated pass for criterion {c.id}: {c.description}"
                for c in required
            ],
        )


__all__ = ["LoopTester"]
