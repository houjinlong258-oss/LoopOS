"""Sandbox path checks for real executor adapters."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path


class SandboxViolation(ValueError):
    """Raised when an executor path escapes its sandbox."""


class SandboxGuard:
    """Validate that executor work stays inside an allowed root."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root).resolve() if root is not None else None

    def ensure_inside(self, path: str | Path) -> Path:
        resolved = Path(path).resolve()
        if self.root is None:
            return resolved
        if resolved == self.root or resolved.is_relative_to(self.root):
            return resolved
        raise SandboxViolation(f"path escapes sandbox: {resolved}")

    def ensure_relative_patch_path(self, path: str) -> None:
        p = Path(path)
        if p.is_absolute() or ".." in p.parts:
            raise SandboxViolation(f"patch path escapes sandbox: {path}")


def copy_to_temp_sandbox(source: str | Path, *, prefix: str = "loopos-exec-") -> Path:
    """Copy a source repo to a temp sandbox and return the new path."""

    src = Path(source).resolve()
    dst = Path(tempfile.mkdtemp(prefix=prefix))
    shutil.copytree(src, dst, dirs_exist_ok=True)
    return dst


__all__ = ["SandboxGuard", "SandboxViolation", "copy_to_temp_sandbox"]
