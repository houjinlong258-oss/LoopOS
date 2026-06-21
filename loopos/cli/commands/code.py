"""CLI commands for the Maintainability Kernel.

Subcommands:
    loopos code summary --diff <file>
    loopos code maintainability --diff <file>
    loopos code gate --report-json <file>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from loopos.maintainability.analyzer import MaintainabilityAnalyzer
from loopos.maintainability.diff_summary import parse_diff
from loopos.maintainability.gate import MaintainabilityGate
from loopos.maintainability.reporter import (
    render_gate_json,
    render_gate_text,
    render_report_json,
    render_report_text,
)


def code_command(args: list[str]) -> None:
    """Entry point for ``loopos code <subcommand>``."""
    if not args:
        _print_usage()
        return

    sub = args[0]
    rest = args[1:]

    if sub == "summary":
        _summary(rest)
    elif sub == "maintainability":
        _maintainability(rest)
    elif sub == "gate":
        _gate(rest)
    else:
        _print_usage()


def _summary(args: list[str]) -> None:
    use_json = "--json" in args
    diff_text = _read_diff(args)
    if diff_text is None:
        return
    summary = parse_diff(diff_text)
    if use_json:
        print(json.dumps(summary.model_dump(mode="json"), indent=2, ensure_ascii=False))
    else:
        print(f"Changed files: {len(summary.changed_files)}")
        print(f"Added: +{summary.added_lines}  Removed: -{summary.removed_lines}")
        if summary.risk_flags:
            print(f"Risk flags: {', '.join(summary.risk_flags)}")
        if summary.new_dependencies:
            print(f"New deps: {', '.join(summary.new_dependencies)}")
        for f in summary.changed_files:
            print(f"  {f}")


def _maintainability(args: list[str]) -> None:
    use_json = "--json" in args
    diff_text = _read_diff(args)
    if diff_text is None:
        return
    summary = parse_diff(diff_text)
    files = _extract_added_lines(diff_text)
    analyzer = MaintainabilityAnalyzer()
    report = analyzer.analyze(summary, files=files)
    if use_json:
        print(render_report_json(report))
    else:
        print(render_report_text(report))


def _gate(args: list[str]) -> None:
    use_json = "--json" in args
    diff_text = _read_diff(args)
    if diff_text is None:
        return
    summary = parse_diff(diff_text)
    files = _extract_added_lines(diff_text)
    analyzer = MaintainabilityAnalyzer()
    report = analyzer.analyze(summary, files=files)
    gate = MaintainabilityGate()
    decision = gate.evaluate(report)
    if use_json:
        print(render_gate_json(decision))
    else:
        print(render_report_text(report))
        print()
        print(render_gate_text(decision))


def _extract_added_lines(diff_text: str) -> dict[str, str]:
    """Group added diff lines by file so content-level rules can run.

    The maintainability analyzer's bypass/complexity/hardcoded-value rules
    operate on file content. From a diff, we synthesize a minimal content map
    by collecting every added (`+`) line under its `+++ b/...` header. This
    lets the CLI surface policy/syscall/data-guard bypasses without needing
    the full working-tree files.
    """

    files: dict[str, list[str]] = {}
    current: str | None = None
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            files.setdefault(current, [])
            continue
        if current is not None and line.startswith("+") and not line.startswith("+++"):
            files[current].append(line[1:])
    return {path: "\n".join(lines) for path, lines in files.items() if lines}


def _read_diff(args: list[str]) -> str | None:
    """Read diff from --diff <file> or stdin."""
    for i, arg in enumerate(args):
        if arg == "--diff" and i + 1 < len(args):
            path = Path(args[i + 1])
            if not path.exists():
                print(f"Error: diff file not found: {path}", file=sys.stderr)
                return None
            return path.read_text(encoding="utf-8")
    # Try reading from stdin if no --diff
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print("Error: provide --diff <file> or pipe diff text to stdin.", file=sys.stderr)
    return None


def _print_usage() -> None:
    print("Usage:")
    print("  loopos code summary --diff <file> [--json]")
    print("  loopos code maintainability --diff <file> [--json]")
    print("  loopos code gate --diff <file> [--json]")
