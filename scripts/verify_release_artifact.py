#!/usr/bin/env python3
"""Verify a LoopOS release ZIP through independent extraction paths."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from loopos.release.artifact_verifier import verify_release_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a LoopOS release artifact.")
    parser.add_argument("artifact")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = verify_release_artifact(args.artifact)
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        for key, value in report.to_dict().items():
            print(f"{key}: {value}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
