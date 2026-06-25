"""Diff evidence helpers for real executor runs."""

from __future__ import annotations

import subprocess
from pathlib import Path


class DiffAnalyzer:
    """Collect changed files and a compact diff summary."""

    def analyze(self, cwd: str | Path) -> tuple[list[str], str]:
        root = Path(cwd).resolve()
        files = subprocess.run(
            ["git", "-C", str(root), "diff", "--name-only"],
            text=True,
            capture_output=True,
            check=False,
        )
        stat = subprocess.run(
            ["git", "-C", str(root), "diff", "--stat"],
            text=True,
            capture_output=True,
            check=False,
        )
        changed = [line.strip() for line in files.stdout.splitlines() if line.strip()]
        return changed, stat.stdout.strip()


__all__ = ["DiffAnalyzer"]
