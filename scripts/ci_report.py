#!/usr/bin/env python3
"""Generate the canonical LoopOS CI/test report.

The release gate treats ``docs/reports/latest-test-report.json`` as a
machine-generated artifact.  This script can either run the local checks
or create a report from explicit CI-provided counts.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _sanitize_local_paths(text: str) -> str:
    """Strip the local repository root from CI output tails.

    The release hygiene scanner flags absolute dev paths (the local repo
    root echoed by pytest/mypy tracbacks) inside release sources.  The CI
    report itself ships inside the source tree, so any such path in the
    output tail would trip the gate.  Rewrite the repo root to a stable
    placeholder so the report stays portable without losing context.
    """

    if not text:
        return text
    candidate = str(_REPO_ROOT)
    replacements = {candidate, candidate.replace("\\", "/")}
    # Also normalize the drive-letter form used by Windows tracbacks.
    drive_form = candidate.replace("/", "\\")
    replacements |= {drive_form, drive_form.replace("\\", "\\\\")}
    sanitized = text
    for token in sorted(replacements, key=len, reverse=True):
        if token:
            sanitized = sanitized.replace(token, "<repo>")
    return sanitized


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate LoopOS CI report JSON.")
    parser.add_argument("--output", default="docs/reports/latest-test-report.json")
    parser.add_argument("--target", default="founding-preview")
    parser.add_argument("--run", action="store_true", help="Run pytest, ruff, and mypy.")
    parser.add_argument("--tests-passed", type=int, default=0)
    parser.add_argument("--subtests-passed", type=int, default=0)
    parser.add_argument("--tests-failed", type=int, default=0)
    parser.add_argument("--ruff", choices=["passed", "failed", "skipped"], default="skipped")
    parser.add_argument("--mypy", choices=["passed", "failed", "skipped"], default="skipped")
    parser.add_argument("--pytest-command", default="python -m pytest")
    parser.add_argument("--ruff-command", default="python -m ruff check .")
    parser.add_argument("--mypy-command", default="python -m mypy loopos tests")
    args = parser.parse_args(argv)

    payload: dict[str, Any] = {
        "schema_version": "1.1",
        "generated_by": "scripts/ci_report.py",
        "target": args.target,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": _git_head(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "offline": True,
        "commands": {
            "pytest": args.pytest_command,
            "ruff": args.ruff_command,
            "mypy": args.mypy_command,
        },
        "tests_passed": args.tests_passed,
        "subtests_passed": args.subtests_passed,
        "tests_failed": args.tests_failed,
        "ruff": args.ruff,
        "mypy": args.mypy,
    }

    exit_code = 0
    if args.run:
        pytest_result = _run_command(args.pytest_command, timeout=240)
        payload["pytest_exit_code"] = pytest_result["exit_code"]
        payload["pytest_output_tail"] = _sanitize_local_paths(pytest_result["tail"])
        counts = _parse_pytest_counts(pytest_result["stdout"] + "\n" + pytest_result["stderr"])
        payload.update(counts)
        if pytest_result["exit_code"] != 0:
            exit_code = 1

        ruff_result = _run_command(args.ruff_command, timeout=90)
        payload["ruff_exit_code"] = ruff_result["exit_code"]
        payload["ruff_output_tail"] = _sanitize_local_paths(ruff_result["tail"])
        payload["ruff"] = "passed" if ruff_result["exit_code"] == 0 else "failed"
        if ruff_result["exit_code"] != 0:
            exit_code = 1

        mypy_result = _run_command(args.mypy_command, timeout=180)
        payload["mypy_exit_code"] = mypy_result["exit_code"]
        payload["mypy_output_tail"] = _sanitize_local_paths(mypy_result["tail"])
        payload["mypy"] = "passed" if mypy_result["exit_code"] == 0 else "failed"
        if mypy_result["exit_code"] != 0:
            exit_code = 1

    output = (Path.cwd() / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(output))
    return exit_code


def _run_command(command: str, *, timeout: int) -> dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=_REPO_ROOT,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    combined = (result.stdout + "\n" + result.stderr).strip()
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "tail": combined[-4000:],
    }


def _parse_pytest_counts(output: str) -> dict[str, int]:
    passed = _last_int(r"(\d+)\s+passed", output)
    failed = _last_int(r"(\d+)\s+failed", output)
    subtests = _last_int(r"(\d+)\s+subtests?\s+passed", output)
    return {
        "tests_passed": passed,
        "tests_failed": failed,
        "subtests_passed": subtests,
    }


def _last_int(pattern: str, text: str) -> int:
    matches = re.findall(pattern, text, flags=re.IGNORECASE)
    return int(matches[-1]) if matches else 0


def _git_head() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


if __name__ == "__main__":
    raise SystemExit(main())
