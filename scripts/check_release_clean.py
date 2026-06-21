#!/usr/bin/env python3
"""Thin CLI wrapper around ``loopos.release.check_release_clean``.

Usage::

    python scripts/check_release_clean.py [--source PATH] [--json]
                                          [--strict]

Exit codes:

  * 0 — clean
  * 1 — one or more blocked violations
  * 2 — usage error

The script auto-adds the repository root to ``sys.path`` so it can be
run directly from a fresh clone without ``pip install -e .``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from loopos.release import check_release_clean  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_release_clean",
        description="Verify a LoopOS source tree is clean enough to release.",
    )
    parser.add_argument(
        "--source",
        "--path",
        dest="source",
        default=".",
        help="Path to the release source tree (default: current directory).",
    )
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Emit the report as a JSON document instead of human-readable text.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings (e.g. leaked dev paths) as errors.",
    )
    parser.add_argument(
        "--ignore-local-only",
        action="store_true",
        help="Ignore gitignored local state such as .loopos, caches, and planning notes.",
    )
    args = parser.parse_args(argv)

    report = check_release_clean(args.source, ignore_local_only=args.ignore_local_only)

    if args.as_json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(f"source: {report.source}")
        print(f"ok: {str(report.ok).lower()}")
        print(f"scanned_files: {report.scanned_files}")
        print(f"scanned_dirs: {report.scanned_dirs}")
        print(f"errors: {len(report.errors)}")
        for f in report.errors:
            loc = f"  {f.path}: " if f.path else "  "
            print(f"  [error] {f.code} {loc}{f.message}".rstrip())
        print(f"warnings: {len(report.warnings)}")
        for f in report.warnings:
            loc = f"  {f.path}: " if f.path else "  "
            print(f"  [warn]  {f.code} {loc}{f.message}".rstrip())

    if not report.ok:
        return 1
    if args.strict and report.warnings:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - executed only when run directly.
    raise SystemExit(main())
