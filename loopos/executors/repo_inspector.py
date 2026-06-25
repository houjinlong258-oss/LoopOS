"""Small repository inspection helpers for the real executor."""

from __future__ import annotations

from pathlib import Path


class RepoInspector:
    """Infer a conservative test command for a repo."""

    def default_test_command(self, repo_path: str | Path) -> list[str]:
        root = Path(repo_path)
        if (root / "pyproject.toml").exists() or (root / "pytest.ini").exists() or (root / "tests").exists():
            import sys

            return [sys.executable, "-m", "pytest", "-q"]
        return []


__all__ = ["RepoInspector"]
