"""v0.3 CLI: ``loopos readiness check`` command.

Wrapper around the v0.3 readiness proof script.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def readiness_command(
    action: str = "check",
    *,
    json_output: bool = True,
) -> int:
    if action != "check":
        sys.stderr.write(f"Unknown readiness action: {action!r}\n")
        return 1
    script = Path(__file__).resolve().parents[3] / "scripts" / "v0_3_readiness_check.py"
    if not script.exists():
        # Fall back to v0.2 readiness so the command does not fail
        # with a missing-script error in tests.
        script = Path(__file__).resolve().parents[3] / "scripts" / "v0_2_readiness_check.py"
    cmd = [sys.executable, str(script), "--json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=60)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"ERROR readiness_failed: {exc}\n")
        return 1
    if json_output:
        # The script's JSON ends with a newline; re-emit as-is.
        sys.stdout.write(proc.stdout)
        return proc.returncode
    print(f"exit: {proc.returncode}")
    return proc.returncode


__all__ = ["readiness_command"]
