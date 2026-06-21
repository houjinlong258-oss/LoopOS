"""Tests for maintainability analysis rules."""

from loopos.maintainability.models import CodeChangeSummary
from loopos.maintainability.rules import (
    check_broad_exception,
    check_bypass_patterns,
    check_complexity,
    check_hardcoded_values,
    check_large_diff,
    check_missing_tests,
)


def test_large_diff_warning() -> None:
    summary = CodeChangeSummary(added_lines=200, removed_lines=150)
    findings = check_large_diff(summary)
    assert len(findings) == 1
    assert findings[0].severity == "warning"
    assert findings[0].category == "large_diff"


def test_large_diff_error() -> None:
    summary = CodeChangeSummary(added_lines=500, removed_lines=400)
    findings = check_large_diff(summary)
    assert len(findings) == 1
    assert findings[0].severity == "error"


def test_large_diff_ok() -> None:
    summary = CodeChangeSummary(added_lines=50, removed_lines=20)
    findings = check_large_diff(summary)
    assert len(findings) == 0


def test_missing_tests_flagged() -> None:
    summary = CodeChangeSummary(
        changed_files=["loopos/kernel/models.py"],
        test_files_changed=[],
    )
    findings = check_missing_tests(summary)
    assert len(findings) == 1
    assert findings[0].category == "missing_test"


def test_missing_tests_ok_when_tests_present() -> None:
    summary = CodeChangeSummary(
        changed_files=["loopos/kernel/models.py", "tests/test_kernel.py"],
        test_files_changed=["tests/test_kernel.py"],
    )
    findings = check_missing_tests(summary)
    assert len(findings) == 0


def test_broad_exception_detected() -> None:
    files = {
        "loopos/core/runner.py": "try:\n    x()\nexcept Exception:\n    pass\n"
    }
    findings = check_broad_exception(files)
    assert len(findings) == 1
    assert findings[0].category == "broad_exception"


def test_hardcoded_secret_detected() -> None:
    files = {
        "loopos/config.py": 'api_key = "sk-1234567890abcdef"\n'
    }
    findings = check_hardcoded_values(files)
    assert len(findings) == 1
    assert findings[0].category == "hardcoded_value"
    assert findings[0].severity == "error"


def test_complexity_long_function() -> None:
    # Generate a function with 150 lines
    lines = ["def long_function():\n"]
    for i in range(150):
        lines.append(f"    x = {i}\n")
    files = {"loopos/big.py": "".join(lines)}
    findings = check_complexity(files)
    assert any(f.category == "complexity" for f in findings)


def test_policy_bypass_detected() -> None:
    files = {
        "loopos/runner.py": 'import subprocess\nsubprocess.run(["ls"])\n'
    }
    findings = check_bypass_patterns(files)
    assert any(f.category == "policy_bypass" for f in findings)


def test_bypass_skipped_in_test_files() -> None:
    files = {
        "tests/test_runner.py": 'import subprocess\nsubprocess.run(["ls"])\n'
    }
    findings = check_bypass_patterns(files)
    assert len(findings) == 0
