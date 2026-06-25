"""Computer-control sandbox helpers."""

from __future__ import annotations

from pathlib import Path


def sandbox_profile_dir(root: str | Path = ".loopos/computer_sandbox") -> Path:
    path = Path(root)
    path.mkdir(parents=True, exist_ok=True)
    return path


__all__ = ["sandbox_profile_dir"]
