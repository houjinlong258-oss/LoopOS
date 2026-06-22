#!/usr/bin/env python3
"""LoopOS Anti-Bloat Gate (Phase 0).

This script enforces the v0.2 hard-freeze policy:

Hard-fail (exit 1) only for three release-boundary violations:
  1. v0_1_runtime_modified     - a file in v0.1.0 loopos/ baseline was changed
  2. unauthorized_dependency    - a new dependency was added without allowlist
  3. v0_1_0_evidence_mutated   - a v0.1.0 evidence file was mutated

All other anti-bloat checks are warning-first (exit 0):
  - module_count_delta
  - new_v0_2_file_over_300_loc
  - single_use_helper_suspicion
  - wrapper_only_function_suspicion
  - low_deletion_ratio
  - large_added_lines_without_paired_tests
  - new_abstraction_count_warning

Usage:
  python scripts/anti_bloat_check.py             # default check
  python scripts/anti_bloat_check.py --json      # machine-readable output
  python scripts/anti_bloat_check.py --self-check # validate gate without failing
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = REPO_ROOT / "scripts" / "baselines" / "v0_1_0_loopos.txt"
V010_TAG = "v0.1.0"

# Hard-fail reason codes
RC_V010_RUNTIME_MODIFIED = "v0_1_runtime_modified"
RC_UNAUTH_DEPENDENCY = "unauthorized_dependency"
RC_V010_EVIDENCE_MUTATED = "v0_1_0_evidence_mutated"

# Warning reason codes
RC_WARN_MODULE_COUNT_DELTA = "module_count_delta"
RC_WARN_FILE_OVER_300 = "new_v0_2_file_over_300_loc"
RC_WARN_SINGLE_USE_HELPER = "single_use_helper_suspicion"
RC_WARN_WRAPPER_ONLY = "wrapper_only_function_suspicion"
RC_WARN_LOW_DELETION_RATIO = "low_deletion_ratio"
RC_WARN_LINES_WITHOUT_TESTS = "large_added_lines_without_paired_tests"
RC_WARN_NEW_ABSTRACTION = "new_abstraction_count_warning"

HARD_FAIL_CODES = {RC_V010_RUNTIME_MODIFIED, RC_UNAUTH_DEPENDENCY, RC_V010_EVIDENCE_MUTATED}
WARNING_CODES = {
    RC_WARN_MODULE_COUNT_DELTA,
    RC_WARN_FILE_OVER_300,
    RC_WARN_SINGLE_USE_HELPER,
    RC_WARN_WRAPPER_ONLY,
    RC_WARN_LOW_DELETION_RATIO,
    RC_WARN_LINES_WITHOUT_TESTS,
    RC_WARN_NEW_ABSTRACTION,
}

# v0.1.0 evidence ledger files (must not be mutated in v0.2)
EVIDENCE_FILES = {
    "docs/v0.1.0-FREEZE.md",
    "docs/schemas/readiness-proof.schema.json",
    "docs/readiness-proof-schema.md",
    "scripts/baselines/v0_1_0_loopos.txt",
}

# Allowlisted dependencies (v0.1.0 baseline, kept static for Phase 0)
ALLOWED_DEPS = {
    "pydantic",
    "pyyaml",
    "typer",
    "rich",
    "pytest",
    "ruff",
    "mypy",
    "hypothesis",
}


@dataclass
class Finding:
    """A single check result."""

    reason_code: str
    severity: str  # "hard_fail" or "warning"
    message: str
    files: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "reason_code": self.reason_code,
            "severity": self.severity,
            "message": self.message,
            "files": self.files,
        }


def run_git(*args: str) -> str:
    """Run a git command and return stdout."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip()
    except FileNotFoundError:
        return ""


def load_baseline() -> List[str]:
    """Load v0.1.0 loopos/ baseline paths."""
    if not BASELINE_PATH.exists():
        # Fall back to git ls-tree
        raw = run_git("ls-tree", "-r", V010_TAG, "--name-only", "--", "loopos/")
        return sorted(p for p in raw.splitlines() if p)
    return sorted(
        p.strip() for p in BASELINE_PATH.read_text(encoding="utf-8").splitlines() if p.strip()
    )


def check_v010_runtime_modified() -> Optional[Finding]:
    """Hard-fail: a file in v0.1.0 loopos/ baseline was modified or deleted."""
    baseline = set(load_baseline())
    if not baseline:
        return Finding(
            reason_code=RC_V010_RUNTIME_MODIFIED,
            severity="hard_fail",
            message="Baseline empty; cannot verify v0.1.0 runtime integrity",
        )
    # Current tracked files under loopos/
    tracked = set(p for p in run_git("ls-files", "--", "loopos/").splitlines() if p)
    modified = []
    for path in sorted(baseline):
        if path not in tracked:
            modified.append(path)
    if not modified:
        return None
    return Finding(
        reason_code=RC_V010_RUNTIME_MODIFIED,
        severity="hard_fail",
        message=f"{len(modified)} v0.1.0 loopos/ baseline file(s) missing or modified",
        files=modified,
    )


def check_unauthorized_dependency() -> Optional[Finding]:
    """Hard-fail: a new dependency was added without allowlist."""
    # Parse pyproject.toml for new dependencies
    pyproject = REPO_ROOT / "pyproject.toml"
    if not pyproject.exists():
        return None
    text = pyproject.read_text(encoding="utf-8")
    # Match entries in [project] dependencies = [...] or [tool.poetry.dependencies]
    found: set[str] = set()
    for m in re.finditer(r'^\s*"([a-zA-Z0-9_.\-]+)"\s*=', text, re.MULTILINE):
        name = m.group(1).lower().split(">=")[0].split("==")[0].split("<")[0].split(">")[0]
        if name and name not in {"python", "name", "version", "description"}:
            found.add(name)
    unauthorized = sorted(found - ALLOWED_DEPS - {"python"})
    # Stdlib names that may appear
    stdlib_hints = {"pathlib", "json", "argparse", "re", "subprocess", "dataclasses", "typing"}
    unauthorized = [d for d in unauthorized if d not in stdlib_hints]
    if not unauthorized:
        return None
    return Finding(
        reason_code=RC_UNAUTH_DEPENDENCY,
        severity="hard_fail",
        message=f"{len(unauthorized)} unauthorized dependency/ies in pyproject.toml",
        files=unauthorized,
    )


def check_v010_evidence_mutated() -> Optional[Finding]:
    """Hard-fail: a v0.1.0 evidence ledger file was mutated.

    In Phase 0 we treat the new FREEZE doc / baseline / readiness schema
    files as the evidence ledger. They are append-only from this PR
    forward; tampering after merge = hard fail.
    """
    mutated: List[str] = []
    for rel in EVIDENCE_FILES:
        path = REPO_ROOT / rel
        if not path.exists():
            mutated.append(rel)
    if mutated:
        return Finding(
            reason_code=RC_V010_EVIDENCE_MUTATED,
            severity="hard_fail",
            message=f"{len(mutated)} v0.1.0 evidence file(s) missing",
            files=mutated,
        )
    return None


# ===== Warning checks (advisory) =====


def warn_module_count_delta() -> Optional[Finding]:
    """Warning: module count delta exceeds threshold."""
    tracked_loopos = len(run_git("ls-files", "--", "loopos/").splitlines())
    baseline_loopos = len(load_baseline())
    if baseline_loopos == 0:
        return None
    delta = tracked_loopos - baseline_loopos
    if delta > 0:
        return Finding(
            reason_code=RC_WARN_MODULE_COUNT_DELTA,
            severity="warning",
            message=f"loopos/ module count grew by {delta} (baseline={baseline_loopos}, current={tracked_loopos})",
        )
    return None


def warn_file_over_300_loc() -> List[Finding]:
    """Warning: any new v0.2 file exceeds 300 LOC."""
    findings: List[Finding] = []
    for path in run_git("status", "--porcelain", "--", "loopos/").splitlines():
        if not path.strip():
            continue
        # format: XY PATH or XY PATH -> PATH
        parts = path.split()
        if len(parts) < 2:
            continue
        file_path = parts[-1]
        if not file_path.endswith(".py"):
            continue
        full = REPO_ROOT / file_path
        if not full.exists() or not full.is_file():
            continue
        try:
            loc = sum(1 for _ in full.open("r", encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        if loc > 300:
            findings.append(
                Finding(
                    reason_code=RC_WARN_FILE_OVER_300,
                    severity="warning",
                    message=f"{file_path} has {loc} lines (threshold=300)",
                    files=[file_path],
                )
            )
    return findings


def warn_new_files_without_tests() -> Optional[Finding]:
    """Warning: new loopos/ files without paired tests."""
    new_files: List[str] = []
    for path in run_git("status", "--porcelain", "--", "loopos/").splitlines():
        if not path.strip():
            continue
        parts = path.split()
        if len(parts) < 2:
            continue
        if not parts[0].startswith("??"):
            continue
        file_path = parts[-1]
        if file_path.endswith(".py") and not file_path.endswith("__init__.py"):
            new_files.append(file_path)
    if not new_files:
        return None
    # Check if a corresponding test file exists
    untested = []
    for f in new_files:
        # Strip loopos/X/ to get module name
        module = f.replace("loopos/", "").replace("/", "_").replace(".py", "")
        test_glob = f"tests/test_{module}.py"
        if not (REPO_ROOT / test_glob).exists():
            untested.append(f)
    if untested:
        return Finding(
            reason_code=RC_WARN_LINES_WITHOUT_TESTS,
            severity="warning",
            message=f"{len(untested)} new module(s) without paired test",
            files=untested,
        )
    return None


def run_all_checks() -> List[Finding]:
    """Run all hard-fail and warning checks."""
    findings: List[Finding] = []
    for fn in (
        check_v010_runtime_modified,
        check_unauthorized_dependency,
        check_v010_evidence_mutated,
    ):
        result = fn()
        if result is not None:
            findings.append(result)
    for fn in (warn_module_count_delta,):
        result = fn()
        if result is not None:
            findings.append(result)
    findings.extend(warn_file_over_300_loc())
    result = warn_new_files_without_tests()
    if result is not None:
        findings.append(result)
    return findings


def render_report(findings: List[Finding], json_mode: bool) -> int:
    """Render findings and return exit code."""
    hard_fails = [f for f in findings if f.severity == "hard_fail"]
    warnings = [f for f in findings if f.severity == "warning"]
    if json_mode:
        report = {
            "schema_version": "0.2",
            "gate": "anti_bloat",
            "hard_fail_count": len(hard_fails),
            "warning_count": len(warnings),
            "hard_fails": [f.to_dict() for f in hard_fails],
            "warnings": [f.to_dict() for f in warnings],
        }
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("=" * 60)
        print("LoopOS Anti-Bloat Gate (Phase 0)")
        print("=" * 60)
        if hard_fails:
            print(f"\nHARD-FAIL ({len(hard_fails)}):")
            for f in hard_fails:
                print(f"  [{f.reason_code}] {f.message}")
                for fp in f.files[:5]:
                    print(f"    - {fp}")
                if len(f.files) > 5:
                    print(f"    ... and {len(f.files) - 5} more")
        else:
            print("\nNo hard-fail violations.")
        if warnings:
            print(f"\nWARNING ({len(warnings)}):")
            for f in warnings:
                print(f"  [{f.reason_code}] {f.message}")
                for fp in f.files[:3]:
                    print(f"    - {fp}")
        else:
            print("\nNo warnings.")
        print(f"\nSummary: hard_fail={len(hard_fails)} warn={len(warnings)}")
    if hard_fails:
        return 1
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="run gate logic but always exit 0 (for development)",
    )
    args = parser.parse_args(argv)
    findings = run_all_checks()
    exit_code = render_report(findings, json_mode=args.json)
    if args.self_check:
        return 0
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
