"""Maintainability analysis rules.

Each rule function accepts a CodeChangeSummary (and optional file content map)
and returns zero or more MaintainabilityFinding items.

Rule categories follow the scoring system:
- large_diff, unrelated_change, missing_test, complexity, duplication
- policy_bypass, syscall_bypass, data_guard_bypass, memory_bypass, trace_bypass
- broad_exception, hardcoded_value, hidden_global_state
"""

from __future__ import annotations

import re
from typing import Any

from loopos.maintainability.models import (
    CodeChangeSummary,
    MaintainabilityFinding,
)

# ---------------------------------------------------------------------------
# Type alias for file content map: {filepath: file_text}
# ---------------------------------------------------------------------------
FileContentMap = dict[str, str]


# ---------------------------------------------------------------------------
# Rule: large diff
# ---------------------------------------------------------------------------
def check_large_diff(summary: CodeChangeSummary) -> list[MaintainabilityFinding]:
    """Flag patches that are too large for reliable review."""
    total = summary.added_lines + summary.removed_lines
    findings: list[MaintainabilityFinding] = []
    if total >= 800:
        findings.append(
            MaintainabilityFinding(
                category="large_diff",
                severity="error",
                message=f"Patch is {total} lines (>= 800). Split into smaller changes.",
                suggested_fix="Break the change into focused commits of ≤ 300 lines each.",
                evidence=[f"added={summary.added_lines} removed={summary.removed_lines}"],
            )
        )
    elif total >= 300:
        findings.append(
            MaintainabilityFinding(
                category="large_diff",
                severity="warning",
                message=f"Patch is {total} lines (>= 300). Consider splitting.",
                evidence=[f"added={summary.added_lines} removed={summary.removed_lines}"],
            )
        )
    return findings


# ---------------------------------------------------------------------------
# Rule: missing tests
# ---------------------------------------------------------------------------
def check_missing_tests(summary: CodeChangeSummary) -> list[MaintainabilityFinding]:
    """Flag source changes that have no corresponding test changes."""
    source_files = [
        f for f in summary.changed_files
        if f.endswith(".py") and "test" not in f.lower() and "__pycache__" not in f
    ]
    if source_files and not summary.test_files_changed:
        return [
            MaintainabilityFinding(
                category="missing_test",
                severity="error",
                message="Source files changed but no test files were modified.",
                suggested_fix="Add or update tests for changed behavior.",
                evidence=source_files[:5],
            )
        ]
    return []


# ---------------------------------------------------------------------------
# Rule: unrelated change detection
# ---------------------------------------------------------------------------
_MODULE_PATTERN = re.compile(r"^(?:loopos|tests)/([^/]+)/")


def check_unrelated_changes(summary: CodeChangeSummary) -> list[MaintainabilityFinding]:
    """Flag changes that span too many unrelated modules."""
    modules: set[str] = set()
    for path in summary.changed_files:
        match = _MODULE_PATTERN.match(path)
        if match:
            modules.add(match.group(1))
    if len(modules) > 4:
        return [
            MaintainabilityFinding(
                category="unrelated_change",
                severity="warning",
                message=f"Change spans {len(modules)} modules: {', '.join(sorted(modules))}",
                suggested_fix="Split into focused changes targeting one module at a time.",
                evidence=sorted(modules),
            )
        ]
    return []


# ---------------------------------------------------------------------------
# Content-based rules (operate on file text)
# ---------------------------------------------------------------------------

def check_broad_exception(files: FileContentMap) -> list[MaintainabilityFinding]:
    """Flag bare ``except Exception`` with pass or log-only handlers."""
    findings: list[MaintainabilityFinding] = []
    pattern = re.compile(r"except\s+(?:Exception|BaseException)\s*(?:as\s+\w+)?:")
    for path, content in files.items():
        for lineno, line in enumerate(content.splitlines(), 1):
            if pattern.search(line):
                findings.append(
                    MaintainabilityFinding(
                        category="broad_exception",
                        severity="warning",
                        file=path,
                        line=lineno,
                        message="Broad exception handler. Catch specific exceptions.",
                        suggested_fix="Replace with specific exception types.",
                        evidence=[line.strip()],
                    )
                )
    return findings


def check_hardcoded_values(files: FileContentMap) -> list[MaintainabilityFinding]:
    """Flag hardcoded secrets, API keys, or environment-specific paths."""
    findings: list[MaintainabilityFinding] = []
    secret_pattern = re.compile(
        r"""(?:api_key|secret|password|token|auth)\s*=\s*["'][^"']{8,}["']""",
        re.IGNORECASE,
    )
    for path, content in files.items():
        for lineno, line in enumerate(content.splitlines(), 1):
            if secret_pattern.search(line):
                findings.append(
                    MaintainabilityFinding(
                        category="hardcoded_value",
                        severity="error",
                        file=path,
                        line=lineno,
                        message="Potential hardcoded secret or credential.",
                        suggested_fix="Use environment variables or a config loader.",
                        evidence=[line.strip()[:80]],
                    )
                )
    return findings


def check_hidden_global_state(files: FileContentMap) -> list[MaintainabilityFinding]:
    """Flag module-level mutable state that can hide runtime behavior."""
    findings: list[MaintainabilityFinding] = []
    global_pattern = re.compile(r"^\s*global\s+\w+", re.MULTILINE)
    for path, content in files.items():
        for lineno, line in enumerate(content.splitlines(), 1):
            if global_pattern.match(line):
                findings.append(
                    MaintainabilityFinding(
                        category="hidden_global_state",
                        severity="warning",
                        file=path,
                        line=lineno,
                        message="Global statement introduces hidden mutable state.",
                        suggested_fix="Pass state explicitly through function parameters.",
                        evidence=[line.strip()],
                    )
                )
    return findings


def check_complexity(files: FileContentMap) -> list[MaintainabilityFinding]:
    """Flag functions that are too long."""
    findings: list[MaintainabilityFinding] = []
    func_pattern = re.compile(r"^(\s*)(?:def|async\s+def)\s+(\w+)\s*\(")
    for path, content in files.items():
        lines = content.splitlines()
        i = 0
        while i < len(lines):
            match = func_pattern.match(lines[i])
            if match:
                indent = len(match.group(1))
                name = match.group(2)
                start = i
                i += 1
                while i < len(lines):
                    stripped = lines[i].rstrip()
                    if stripped == "":
                        i += 1
                        continue
                    current_indent = len(stripped) - len(stripped.lstrip())
                    if current_indent <= indent and stripped.lstrip() and not stripped.lstrip().startswith(("#", "\"\"\"", "'''")):
                        break
                    i += 1
                length = i - start
                if length > 200:
                    findings.append(
                        MaintainabilityFinding(
                            category="complexity",
                            severity="error",
                            file=path,
                            line=start + 1,
                            symbol=name,
                            message=f"Function '{name}' is {length} lines (> 200).",
                            suggested_fix="Extract helper functions to reduce complexity.",
                            evidence=[f"lines {start + 1}-{i}"],
                        )
                    )
                elif length > 100:
                    findings.append(
                        MaintainabilityFinding(
                            category="complexity",
                            severity="warning",
                            file=path,
                            line=start + 1,
                            symbol=name,
                            message=f"Function '{name}' is {length} lines (> 100).",
                            suggested_fix="Consider splitting into smaller functions.",
                            evidence=[f"lines {start + 1}-{i}"],
                        )
                    )
            else:
                i += 1
    return findings


# ---------------------------------------------------------------------------
# Bypass detection rules
# ---------------------------------------------------------------------------

_BYPASS_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "policy_bypass",
        re.compile(r"(?:os\.system|subprocess\.(?:call|run|Popen))\s*\("),
        "Direct shell call detected — must route through Syscall Router.",
    ),
    (
        "syscall_bypass",
        re.compile(r"(?:open|pathlib\.Path)\s*\(.*['\"]w['\"]"),
        "Direct file write detected — must use file.write syscall.",
    ),
    (
        "data_guard_bypass",
        re.compile(r"(?:cursor\.execute|\.executemany|\.executescript)\s*\(.*(?:DROP|ALTER|DELETE|TRUNCATE|UPDATE)", re.IGNORECASE),
        "Destructive SQL without Data Guard — must route through Data Guard.",
    ),
    (
        "memory_bypass",
        re.compile(r"memory.*\.(?:write|commit|persist|save_permanent)\s*\(", re.IGNORECASE),
        "Direct durable memory write — must use Memory Governance.",
    ),
    (
        "trace_bypass",
        re.compile(r"requests\.(?:get|post|put|delete|patch)\s*\("),
        "External HTTP call without trace — must log through trace store.",
    ),
]


def check_bypass_patterns(files: FileContentMap) -> list[MaintainabilityFinding]:
    """Detect patterns that bypass LoopOS governance layers."""
    findings: list[MaintainabilityFinding] = []
    for path, content in files.items():
        # Skip test files — they are allowed to use mocks
        if "test" in path.lower():
            continue
        for lineno, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for category, pattern, message in _BYPASS_PATTERNS:
                if pattern.search(line):
                    severity: Any = "blocker" if category in {
                        "policy_bypass", "data_guard_bypass", "memory_bypass"
                    } else "error"
                    findings.append(
                        MaintainabilityFinding(
                            category=category,  # type: ignore[arg-type]
                            severity=severity,
                            file=path,
                            line=lineno,
                            message=message,
                            evidence=[stripped[:120]],
                        )
                    )
    return findings
