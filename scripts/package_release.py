#!/usr/bin/env python3
"""Thin CLI wrapper around ``loopos.release.package_release``.

Usage::

    python scripts/package_release.py \\
        --version 0.1.0 \\
        --output dist/ \\
        [--source .] \\
        [--no-zip] \\
        [--json]

Exit codes:

  * 0 — artifact built successfully
  * 1 — staging or packaging error
  * 2 — usage error

The script auto-adds the repository root to ``sys.path`` so it can be
run directly from a fresh clone without ``pip install -e .``.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from loopos.release import check_release_clean, package_release  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="package_release",
        description="Build a clean LoopOS release artifact.",
    )
    parser.add_argument("--version", required=True, help="Release version string.")
    parser.add_argument(
        "--source",
        default=".",
        help="Path to the source tree to package (default: current directory).",
    )
    parser.add_argument(
        "--output",
        default="dist",
        help="Directory to write the staged tree and zip into (default: dist).",
    )
    parser.add_argument(
        "--no-zip",
        dest="make_zip",
        action="store_false",
        help="Skip writing the .zip archive (still writes the staging dir).",
    )
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Emit the report as JSON instead of human-readable text.",
    )
    parser.add_argument(
        "--strict-source",
        action="store_true",
        help="Fail if the source tree itself contains release hygiene findings.",
    )
    args = parser.parse_args(argv)

    if args.strict_source:
        source_report = check_release_clean(args.source, ignore_local_only=False)
        if not source_report.ok or source_report.warnings:
            if args.as_json:
                payload = source_report.to_dict()
                payload["strict_source"] = True
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print("strict source preflight failed")
                print(f"errors: {len(source_report.errors)}")
                for finding in source_report.errors[:20]:
                    loc = f" {finding.path}:" if finding.path else ""
                    print(f"  [error] {finding.code}{loc} {finding.message}")
                print(f"warnings: {len(source_report.warnings)}")
                for finding in source_report.warnings[:20]:
                    loc = f" {finding.path}:" if finding.path else ""
                    print(f"  [warn] {finding.code}{loc} {finding.message}")
            return 1

    report = package_release(
        version=args.version,
        source=args.source,
        output=args.output,
        make_zip=args.make_zip,
    )

    if args.as_json:
        payload = report.to_dict()
        payload["built_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"version: {report.version}")
        print(f"source: {report.source}")
        print(f"staging_dir: {report.staging_dir}")
        print(f"manifest: {report.manifest_path}")
        print(f"sha256: {report.sha256_path}")
        if report.zip_path:
            print(f"zip: {report.zip_path}")
        print(f"copied_files: {report.copied_files}")
        print(f"errors: {len(report.errors)}")
        for err in report.errors:
            print(f"  [error] {err}")

    if report.errors:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - executed only when run directly.
    raise SystemExit(main())
