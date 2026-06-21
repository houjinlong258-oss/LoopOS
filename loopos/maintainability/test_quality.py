"""Test-quality rules for the Maintainability Kernel.

Heuristics for detecting weak tests that pass but do not actually verify
behavior: tests with no assertions, tests that only check ``is not None``,
tests with ``assert True``, and tests that swallow failures behind
``try/except: pass``.
"""

from __future__ import annotations

import re

from loopos.maintainability.models import CodeChangeSummary, MaintainabilityFinding

_ASSERT_PATTERN = re.compile(r"\bassert\b")
_TRIVIAL_ASSERT_PATTERN = re.compile(r"assert\s+(True|1|not\s+None)(\s*,|\s*$)")
_TRY_PASS_PATTERN = re.compile(r"except\s+\w+.*:\s*\n\s*pass", re.MULTILINE)
_NO_ASSERT_DECORATOR_PATTERN = re.compile(r"@pytest\.mark\.(?:skip|xfail)")


class TestQualityRules:
    """Detect weak tests in the changed test files."""

    def check(
        self,
        summary: CodeChangeSummary,
        files: dict[str, str],
    ) -> list[MaintainabilityFinding]:
        findings: list[MaintainabilityFinding] = []
        for path in summary.test_files_changed:
            content = files.get(path)
            if content is None:
                continue
            findings.extend(self._check_one(path, content))
        if summary.test_files_changed and not any(
            self._has_real_assertion(files.get(p, "")) for p in summary.test_files_changed
        ):
            findings.append(
                MaintainabilityFinding(
                    category="weak_test",
                    severity="warning",
                    message="Changed test files contain no real assertions.",
                    suggested_fix="Add assertions that verify observable behavior.",
                    evidence=summary.test_files_changed[:5],
                )
            )
        return findings

    def _check_one(self, path: str, content: str) -> list[MaintainabilityFinding]:
        findings: list[MaintainabilityFinding] = []
        if _NO_ASSERT_DECORATOR_PATTERN.search(content):
            findings.append(
                MaintainabilityFinding(
                    category="weak_test",
                    severity="info",
                    file=path,
                    message="Test uses @pytest.mark.skip or @pytest.mark.xfail.",
                    suggested_fix="Remove the marker or make the test meaningful.",
                )
            )
        if _TRY_PASS_PATTERN.search(content):
            findings.append(
                MaintainabilityFinding(
                    category="weak_test",
                    severity="warning",
                    file=path,
                    message="Test swallows exceptions with try/except: pass.",
                    suggested_fix="Let the exception propagate or assert the expected error.",
                )
            )
        for lineno, line in enumerate(content.splitlines(), 1):
            if _TRIVIAL_ASSERT_PATTERN.search(line):
                findings.append(
                    MaintainabilityFinding(
                        category="weak_test",
                        severity="info",
                        file=path,
                        line=lineno,
                        message="Trivial assertion (assert True / assert 1 / assert not None).",
                        suggested_fix="Assert a concrete expected value.",
                        evidence=[line.strip()],
                    )
                )
        return findings

    def _has_real_assertion(self, content: str) -> bool:
        if not content:
            return False
        if not _ASSERT_PATTERN.search(content):
            return False
        for line in content.splitlines():
            stripped = line.strip()
            if _ASSERT_PATTERN.search(stripped) and not _TRIVIAL_ASSERT_PATTERN.search(stripped):
                return True
        return False
